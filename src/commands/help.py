import discord
from discord.ext import commands
from src.config import BOT_CONFIG

@commands.command(name='help', aliases=['?'])
async def custom_help(ctx):
    """コマンドのヘルプを表示するコマンド"""
    embed = discord.Embed(
        title="📔 Discord日記ボット ヘルプ",
        description="シンプルに日記を記録・管理するためのボットです。",
        color=0x3498db
    )
    
    commands_info = [
        {
            "name": "!new (!n)",
            "value": "新しい日記を作成します。テンプレートが表示され、返信することで日記を書けます。"
        },
        {
            "name": "!today (!t)",
            "value": "今日の日記を表示します。まだ書いていない場合は通知されます。"
        },
        {
            "name": "!history (!h) [オプション]",
            "value": "日記の履歴を表示します。オプション:\n・数字なし: 今日の日記\n・数字: 指定した日数前の日記（1=昨日）\n・日付: 指定した日の日記（YYYY-MM-DD形式）\n・all: すべての日記一覧"
        },
        {
            "name": "!search (!s) キーワード",
            "value": "日記をキーワードで検索します。"
        },
        {
            "name": "!update (!u)",
            "value": "今日の日記を更新します。現在の内容が表示され、返信することで更新できます。"
        },
        {
            "name": "!delete (!d)",
            "value": "今日の日記を削除します。確認メッセージが表示されます。"
        }
    ]
    
    for cmd in commands_info:
        embed.add_field(name=cmd["name"], value=cmd["value"], inline=False)
    
    embed.set_footer(text="日記は1日1件までです。新しく書くと上書きされます。")
    
    await ctx.send(embed=embed)