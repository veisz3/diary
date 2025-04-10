#!/usr/bin/env python

import os
import json
import requests
from datetime import datetime, timedelta
from github import Github
import re

# 環境変数から情報を取得
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")  # GitHub Actionsで自動的に設定される

# GitHubクライアントの初期化
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

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
        
        return new_entries
    except Exception as e:
        print(f"エラー: {e}")
        return []

def review_with_gemini(entry_content):
    """Gemini APIを使用して日記エントリをレビューする"""
    try:
        # 不要なマークダウン記法を取り除いて、純粋な内容部分を抽出
        content_section = re.search(r'## 内容\n([\s\S]*?)(?=\n##|\Z)', entry_content)
        if content_section:
            diary_text = content_section.group(1).strip()
        else:
            diary_text = entry_content
        
        # APIエンドポイント
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        
        # リクエストボディ
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""以下は日記の内容です。この日記に対して、以下の観点からポジティブなレビューとアドバイスを短く（100〜200文字程度）提供してください：

1. 良かった点を1つ挙げる
2. もっと詳しく知りたい点を1つ挙げる
3. 文章の流れについてのアドバイス

日記の内容：
{diary_text}

レビュー："""
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 500
            }
        }
        
        # APIリクエスト
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            review_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return review_text
        else:
            print(f"APIエラー ({response.status_code}): {response.text}")
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
                        "name": "🤖 AIレビュー",
                        "value": review,
                        "inline": False
                    }
                ]
            }]
        }
        
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

def main():
    """メイン処理"""
    print(f"== {yesterday_str}の日記エントリをチェックしています ==")
    
    # 新しいエントリを取得
    new_entries = get_new_entries()
    
    if not new_entries:
        print(f"新しい日記エントリは見つかりませんでした")
        
        # エントリがない場合もDiscordに通知
        empty_message = {
            "content": f"📅 {yesterday_str}の日記エントリはありませんでした。今日はどんな一日でしたか？"
        }
        requests.post(DISCORD_WEBHOOK_URL, json=empty_message)
        return
    
    print(f"{len(new_entries)}件の新しい日記エントリを見つけました")
    
    # 各エントリをレビュー
    for entry in new_entries:
        print(f"レビュー中: {entry['path']}")
        review = review_with_gemini(entry["content"])
        
        # Discordに送信
        send_to_discord(entry, review)
    
    print("== 処理完了 ==")

if __name__ == "__main__":
    main()
