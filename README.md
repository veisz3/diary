# Discord日記ボット

Discordでチャットした内容をGitHubにMarkdownファイルとして保存し、AIによる日記レビューを自動化するボットです。

## 🌟 機能

- ✅ 指定したDiscordチャンネルでの会話を自動的に日記として記録
- 📂 GitHubにMarkdownファイルとして整理して保存
- 🔍 日付ごとの日記エントリの閲覧機能
- ✏️ 過去の日記エントリの更新機能
- 🤖 Gemini APIによる日記のAIレビュー機能
- 🔔 レビュー結果のDiscord通知機能

## 🚀 セットアップ方法

### 前提条件

- Pythonがインストールされていること (3.8以上推奨)
- Discordアカウントとボットの作成権限
- GitHubアカウントとリポジトリ
- Google Cloud Platform (Gemini API用)
- Koyebアカウント (デプロイ用、省略可能)

### 手順

#### 1. Discordボットの作成
1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」をクリックして新しいアプリケーションを作成
3. 「Bot」タブからボットを作成し、トークンを取得
4. 「OAuth2」タブから必要な権限を設定し、招待URLを生成
5. 生成されたURLからボットをサーバーに招待

#### 2. GitHubリポジトリの設定
1. GitHubで新しいリポジトリを作成
2. Personal Access Tokenを生成 (リポジトリへの書き込み権限が必要)

#### 3. Gemini APIの設定
1. [Google AI Studio](https://makersuite.google.com/app/apikey)でAPI Keyを取得

#### 4. ボットのセットアップとローカル実行
1. `.env`ファイルを編集して、各種キーやトークンを設定
2. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
3. ボットを実行
   ```
   python main.py
   ```

## 💬 使い方

### 基本的な使い方
- 指定したチャンネルで会話するだけで自動的に記録されます
- メッセージが保存されると「📝」リアクションが追加されます

### コマンド
- `!history [日付]` - 指定した日付の日記履歴を表示します（日付の形式: YYYY-MM-DD）
- `!update [ファイルパス] [新しい内容]` - 指定した日記エントリを更新します

### AIレビュー
- 毎日0時（UTC）に前日の日記エントリに対してGemini APIによるレビューが実行されます
- レビュー結果はDiscordに通知されます

## 📋 環境変数

`.env`ファイルに以下の環境変数を設定してください：

```
# Discord Bot設定
DISCORD_TOKEN=your_discord_bot_token_here
ALLOWED_CHANNELS=channel_id1,channel_id2

# GitHub設定
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=username/repository_name

# Gemini API設定
GEMINI_API_KEY=your_gemini_api_key_here

# Discord Webhook URL（GitHub Actionsの通知用）
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

## 📚 技術スタック

- **バックエンド**: Python, discord.py
- **データストレージ**: GitHub (Markdownファイル)
- **AI機能**: Google Gemini API
- **デプロイ**: ローカル実行またはKoyeb
- **自動化**: GitHub Actions

## 📄 ライセンス

MIT
