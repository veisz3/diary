import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# 設定をまとめたディクショナリ
BOT_CONFIG = {
    "DISCORD_TOKEN": os.getenv('DISCORD_TOKEN'),
    "GITHUB_TOKEN": os.getenv('GITHUB_TOKEN'),
    "GITHUB_REPO": 'veisz3/diary-repo',
    "ALLOWED_CHANNELS": list(map(int, os.getenv('ALLOWED_CHANNELS').split(','))),
    "COMMAND_PREFIX": "!",
    # 1日1件の制限（同じ日・同じユーザーの場合は上書き）
    "ONE_ENTRY_PER_DAY": True
}