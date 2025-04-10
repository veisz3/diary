import datetime
import base64
from github import Github, GithubException
from src.config import BOT_CONFIG

# GitHubクライアントの初期化
github_client = Github(BOT_CONFIG["GITHUB_TOKEN"])

async def save_message_to_github(message, author_name, channel_name, content=None, template=False):
    """メッセージをGitHubのマークダウンファイルとして保存する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # 現在の日付を取得してファイル名を生成
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"diary/{today}/{author_name}_{timestamp}.md"
        
        # マークダウンコンテンツの作成
        if content is None:
            content = message.content if hasattr(message, 'content') else ""
            
        entry_content = f"""# {author_name}の日記エントリ

## 日時
{datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## チャンネル
{channel_name}

## 内容
{content}

"""
        
        # テンプレート機能
        if template:
            entry_content = f"""# {author_name}の日記エントリ

## 日時
{datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

## チャンネル
{channel_name}

## 今日の気分
(ここに気分を書いてください)

## 今日やったこと
(ここに今日やったことを書いてください)

## 明日の予定
(ここに明日の予定を書いてください)

## 感想・反省
(ここに感想や反省を書いてください)

"""
        
        # 添付ファイルがある場合は記述を追加（URLのみ）
        if hasattr(message, 'attachments') and message.attachments:
            entry_content += "\n## 添付ファイル\n"
            for attachment in message.attachments:
                entry_content += f"- [{attachment.filename}]({attachment.url})\n"
        
        # ファイルの作成（フォルダがなければ作成）
        try:
            # diaryフォルダが存在するか確認
            try:
                repo.get_contents("diary")
            except GithubException:
                # diary フォルダが存在しない場合は作成
                repo.create_file(
                    "diary/.gitkeep",
                    "Create diary folder",
                    ""
                )
            
            # 日付フォルダが存在するか確認
            try:
                repo.get_contents(f"diary/{today}")
            except GithubException:
                # フォルダが存在しない場合は作成
                repo.create_file(
                    f"diary/{today}/.gitkeep",
                    f"Create diary folder for {today}",
                    ""
                )
                
            # 既存のエントリを確認（1日1件制限の場合）
            if BOT_CONFIG.get("ONE_ENTRY_PER_DAY", True):
                try:
                    contents = repo.get_contents(f"diary/{today}")
                    for content_file in contents:
                        if content_file.name.endswith('.md') and author_name in content_file.name:
                            # 既存の日記を上書き
                            return await update_diary_entry(content_file.path, content)
                except Exception as e:
                    print(f"Error checking existing entries: {e}")
            
            # ファイルを作成
            result = repo.create_file(
                filename,
                f"Add diary entry from {author_name}",
                entry_content
            )
            return True, filename
        except GithubException as e:
            print(f"GitHub error: {e}")
            return False, str(e)
    except Exception as e:
        print(f"Error saving to GitHub: {e}")
        return False, str(e)

async def get_file_content(file_path):
    """ファイルの内容を取得する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # ファイルの取得
        file = repo.get_contents(file_path)
        content = base64.b64decode(file.content).decode('utf-8')
        
        return True, content
    except GithubException as e:
        print(f"GitHub error when getting file: {e}")
        return False, str(e)
    except Exception as e:
        print(f"Error getting file content: {e}")
        return False, str(e)

async def get_diary_entries(date=None):
    """指定した日付（デフォルトは今日）の日記エントリを取得する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # 日付の処理
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        elif isinstance(date, int):
            # 相対日数の場合
            target_date = datetime.datetime.now() - datetime.timedelta(days=date)
            date = target_date.strftime('%Y-%m-%d')
        
        # 指定したフォルダ内のファイルを取得
        folder_path = f"diary/{date}"
        try:
            contents = repo.get_contents(folder_path)
            
            entries = []
            for content_file in contents:
                if content_file.name.endswith('.md'):
                    file_content = base64.b64decode(content_file.content).decode('utf-8')
                    entries.append({
                        'filename': content_file.name,
                        'content': file_content,
                        'path': content_file.path
                    })
            
            return True, entries
        except GithubException:
            return False, f"日付 {date} の日記エントリは見つかりませんでした。"
    except Exception as e:
        print(f"Error fetching diary entries: {e}")
        return False, str(e)

async def get_all_diary_entries():
    """すべての日記エントリの一覧を取得する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # diaryフォルダが存在するか確認
        try:
            diary_contents = repo.get_contents("diary")
            
            # 日付フォルダのリスト
            date_folders = []
            for item in diary_contents:
                if item.type == "dir":
                    date_folders.append(item.path)
            
            # 全てのエントリをまとめて取得
            all_entries = []
            
            for folder in sorted(date_folders, reverse=True):  # 新しい日付順
                date = folder.split('/')[-1]
                try:
                    folder_contents = repo.get_contents(folder)
                    
                    for content_file in folder_contents:
                        if content_file.name.endswith('.md'):
                            file_content = base64.b64decode(content_file.content).decode('utf-8')
                            all_entries.append({
                                'date': date,
                                'filename': content_file.name,
                                'content': file_content,
                                'path': content_file.path
                            })
                except GithubException:
                    continue
            
            return True, all_entries
        except GithubException:
            return False, "日記フォルダが見つかりませんでした。"
    except Exception as e:
        print(f"Error fetching all diary entries: {e}")
        return False, str(e)

async def update_diary_entry(file_path, new_content):
    """日記エントリを更新する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # ファイルの取得
        file = repo.get_contents(file_path)
        old_content = base64.b64decode(file.content).decode('utf-8')
        
        # 内容セクションを更新
        lines = old_content.split('\n')
        new_lines = []
        content_section = False
        content_replaced = False
        
        for line in lines:
            if line.startswith('## 内容'):
                content_section = True
                new_lines.append(line)
                new_lines.append(new_content)
                content_replaced = True
            elif content_section and (line.startswith('##') or not line and lines.index(line)+1 < len(lines) and not lines[lines.index(line)+1]):
                content_section = False
                new_lines.append(line)
            elif not content_section:
                new_lines.append(line)
        
        # ヘッダーセクションのみの更新なら全体を更新
        if not content_replaced:
            # 現在のヘッダー情報を保持
            header_lines = []
            for line in lines:
                if line.startswith('# ') or line.startswith('## 日時') or line.startswith('## チャンネル'):
                    header_lines.append(line)
                elif line.startswith('## 内容'):
                    break
            
            # 新しい内容と結合
            new_lines = header_lines + ['## 内容', new_content]
                
        # 更新されたコンテンツ
        updated_content = '\n'.join(new_lines)
        
        # ファイルの更新
        result = repo.update_file(
            file_path,
            f"Update diary entry",
            updated_content,
            file.sha
        )
        
        return True, file_path
    except GithubException as e:
        print(f"GitHub error when updating: {e}")
        return False, str(e)
    except Exception as e:
        print(f"Error updating diary entry: {e}")
        return False, str(e)

async def delete_diary_entry(file_path):
    """日記エントリを削除する"""
    try:
        # リポジトリの取得
        repo = github_client.get_repo(BOT_CONFIG["GITHUB_REPO"])
        
        # ファイルの取得
        file = repo.get_contents(file_path)
        
        # ファイルの削除
        result = repo.delete_file(
            file_path,
            f"Delete diary entry",
            file.sha
        )
        
        return True, "削除しました"
    except GithubException as e:
        print(f"GitHub error when deleting: {e}")
        return False, str(e)
    except Exception as e:
        print(f"Error deleting entry: {e}")
        return False, str(e)

async def get_diary_by_date_range(start_date, end_date):
    """指定した日付範囲の日記エントリを取得する"""
    try:
        # 日付の処理
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # 日付の範囲内のすべての日を生成
        date_range = []
        current = start
        while current <= end:
            date_range.append(current.strftime('%Y-%m-%d'))
            current += datetime.timedelta(days=1)
        
        # 各日付の日記を取得
        all_entries = []
        for date in date_range:
            success, entries = await get_diary_entries(date)
            if success and entries:
                for entry in entries:
                    entry['date'] = date
                    all_entries.append(entry)
        
        if all_entries:
            return True, all_entries
        else:
            return False, "指定した期間に日記エントリは見つかりませんでした。"
    except Exception as e:
        print(f"Error fetching diary entries by date range: {e}")
        return False, str(e)

async def search_diary_entries(keyword):
    """日記エントリをキーワードで検索する"""
    try:
        # すべての日記エントリを取得
        success, all_entries = await get_all_diary_entries()
        
        if not success:
            return False, all_entries
        
        # キーワードでフィルタリング
        matched_entries = []
        for entry in all_entries:
            if keyword.lower() in entry['content'].lower():
                matched_entries.append(entry)
        
        if matched_entries:
            return True, matched_entries
        else:
            return False, f"キーワード '{keyword}' を含む日記エントリは見つかりませんでした。"
    except Exception as e:
        print(f"Error searching diary entries: {e}")
        return False, str(e)