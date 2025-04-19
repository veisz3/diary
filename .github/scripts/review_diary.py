#!/usr/bin/env python

import os
import json
import requests
from datetime import datetime, timedelta
from github import Github
import re
import sys

# 環境変数から情報を取得
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# REPO_NAME = os.environ.get("GITHUB_REPOSITORY")  # GitHub Actionsで自動的に設定される
REPO_NAME = 'veisz3/diary-repo'

# 環境変数チェック
missing_vars = []
if not GITHUB_TOKEN:
    missing_vars.append("GITHUB_TOKEN")
if not CLAUDE_API_KEY:
    missing_vars.append("CLAUDE_API_KEY")
if not DISCORD_WEBHOOK_URL:
    missing_vars.append("DISCORD_WEBHOOK_URL")
if not REPO_NAME:
    missing_vars.append("GITHUB_REPOSITORY")

if missing_vars:
    print(f"エラー: 以下の環境変数が設定されていません: {', '.join(missing_vars)}")
    sys.exit(1)

# Webhook URL の形式を確認
if not DISCORD_WEBHOOK_URL.startswith(('http://', 'https://')):
    print(f"エラー: DISCORD_WEBHOOK_URL の形式が正しくありません: {DISCORD_WEBHOOK_URL}")
    sys.exit(1)

# GitHubクライアントの初期化
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    print(f"リポジトリの情報: {repo.full_name}")
except Exception as e:
    print(f"GitHubリポジトリへの接続エラー: {e}")
    sys.exit(1)

# 日付の設定
today = datetime.now()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.strftime('%Y-%m-%d')

def get_new_entries():
    """昨日追加された新しい日記エントリを取得"""
    new_entries = []
    
    try:
        # 昨日のフォルダをチェック
        diary_folder = f"diary/{yesterday_str}"
        print(f"フォルダをチェック中: {diary_folder}")
        
        try:
            contents = repo.get_contents(diary_folder)
            
            # .mdファイルのみを取得
            for content in contents:
                if content.path.endswith('.md'):
                    # ファイルの内容を取得
                    file_content = content.decoded_content.decode('utf-8')
                    new_entries.append({
                        "path": content.path,
                        "content": file_content
                    })
            
            print(f"{len(new_entries)}件のマークダウンファイルを見つけました")
        except Exception as e:
            print(f"フォルダが見つからないか内容の取得に失敗しました: {e}")
            # フォルダが見つからなくても正常終了させる
            return []
        
        return new_entries
    except Exception as e:
        print(f"エントリ取得エラー: {e}")
        return []

def review_with_claude(entry_content):
    """Claude APIを使用して日記エントリをレビューする"""
    try:
        # 不要なマークダウン記法を取り除いて、純粋な内容部分を抽出
        content_section = re.search(r'## 内容\n([\s\S]*?)(?=\n##|\Z)', entry_content)
        if content_section:
            diary_text = content_section.group(1).strip()
        else:
            diary_text = entry_content
        
        # Claude API エンドポイント
        url = "https://api.anthropic.com/v1/messages"
        
        # リクエストヘッダー
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # リクエストボディ
        payload = {
            "model": "claude-3-opus-20240229",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": f"""以下は日記の内容です。この日記に対して、以下の観点からポジティブなレビューとアドバイスを短く（100〜200文字程度）提供してください：

1. 良かった点を1つ挙げる
2. もっと詳しく知りたい点を1つ挙げる
3. 文章の流れについてのアドバイス

日記の内容：
{diary_text}"""
                }
            ]
        }
        
        print("Claude APIにリクエスト送信中...")
        
        # APIリクエスト
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # Claude APIはcontent配列を返すため、テキスト部分を抽出
            review_text = result["content"][0]["text"]
            return review_text
        else:
            print(f"Claude APIエラー ({response.status_code}): {response.text}")
            return "レビューの取得中にエラーが発生しました。"
    except Exception as e:
        print(f"レビュー中のエラー: {e}")
        return "レビュー処理中にエラーが発生しました。"

def send_to_discord(entry, review):
    """レビュー結果をDiscordに送信"""
    try:
        # 日記のタイトルと書いた人を抽出
        author_match = re.search(r'# (.+?)の日記エントリ', entry["content"])
        author = author_match.group(1) if author_match else "不明"
        
        # メッセージの構成
        message = {
            "embeds": [{
                "title": f"📝 {author}さんの日記レビュー",
                "description": f"{yesterday_str}の日記へのAIレビューです",
                "color": 0x3498db,
                "fields": [
                    {
                        "name": "📄 ファイル",
                        "value": entry["path"],
                        "inline": True
                    },
                    {
                        "name": "🤖 Claude AIのレビュー",
                        "value": review,
                        "inline": False
                    }
                ]
            }]
        }
        
        print(f"Discordに通知を送信中: {DISCORD_WEBHOOK_URL[:30]}...")
        
        # Discordウェブフックに送信
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=message
        )
        
        if response.status_code == 204:
            print(f"Discord通知成功: {entry['path']}")
            return True
        else:
            print(f"Discord通知エラー ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"Discord送信エラー: {e}")
        return False

def send_empty_notification():
    """エントリがない場合のDiscord通知"""
    try:
        # エントリがない場合のメッセージ
        empty_message = {
            "content": f"📅 {yesterday_str}の日記エントリはありませんでした。今日はどんな一日でしたか？"
        }
        
        print(f"エントリなしの通知を送信中: {DISCORD_WEBHOOK_URL[:30]}...")
        
        # Discordウェブフックに送信
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=empty_message
        )
        
        if response.status_code == 204:
            print("Discord通知成功: エントリなし")
            return True
        else:
            print(f"Discord通知エラー ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"Discord送信エラー: {e}")
        return False

def main():
    """メイン処理"""
    print(f"== {yesterday_str}の日記エントリをチェックしています ==")
    
    # 新しいエントリを取得
    new_entries = get_new_entries()
    
    if not new_entries:
        print(f"新しい日記エントリは見つかりませんでした")
        
        # エントリがない場合もDiscordに通知
        send_empty_notification()
        return
    
    print(f"{len(new_entries)}件の新しい日記エントリを見つけました")
    
    # 各エントリをレビュー
    for entry in new_entries:
        print(f"レビュー中: {entry['path']}")
        review = review_with_claude(entry["content"])
        
        # Discordに送信
        send_to_discord(entry, review)
    
    print("== 処理完了 ==")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        sys.exit(1)
