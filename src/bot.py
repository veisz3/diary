import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# モジュールのインポート
from src.commands import diary, history, help
from src.config import BOT_CONFIG

# 環境変数の読み込み
load_dotenv()

# Botの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Botが準備完了したときに呼ばれる"""
    print(f'{bot.user} としてログインしました！')
    print(f'対象チャンネル: {BOT_CONFIG["ALLOWED_CHANNELS"]}')

@bot.event
async def on_message(message):
    # 基本的なメッセージハンドリング
    # ...
    
    # コマンド処理を続行
    await bot.process_commands(message)

# コマンドの登録
bot.add_command(diary.new_entry)
bot.add_command(diary.update_entry)
bot.add_command(diary.delete_entry)
bot.add_command(history.get_history)
bot.add_command(history.today_entry)
bot.remove_command('help')
bot.add_command(help.custom_help)

def run_bot():
    """Botを実行する"""
    bot.run(os.getenv('DISCORD_TOKEN'))