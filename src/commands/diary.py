import discord
from discord.ext import commands
import asyncio
import datetime
from src.utils.github_utils import save_message_to_github, update_diary_entry, delete_diary_entry, get_diary_entries
from src.config import BOT_CONFIG

@commands.command(name='new', aliases=['n'])
async def new_entry(ctx):
    """新しい日記エントリを作成するコマンド（インタラクティブ）"""
    # 許可されたチャンネルかチェック
    if ctx.channel.id not in BOT_CONFIG["ALLOWED_CHANNELS"]:
        await ctx.send("❌ このチャンネルでは日記を記録できません。")
        return
    
    # テンプレートを送信
    template_text = """
# 今日の気分
(ここに気分を書いてください)

# 今日やったこと
(ここに今日やったことを書いてください)

# 明日の予定
(ここに明日の予定を書いてください)

# 感想・反省
(ここに感想や反省を書いてください)
"""
    
    template_msg = await ctx.send(f"以下のテンプレートを参考に、返信で日記を書いてください：\n```markdown{template_text}```\n※5分以内に返信してください。キャンセルするには「キャンセル」と入力してください。")
    
    # 返信を待つ
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and (
            m.reference is not None and m.reference.message_id == template_msg.id
        )
    
    try:
        # 5分間返信を待つ
        reply = await ctx.bot.wait_for('message', check=check, timeout=300.0)
        
        # キャンセルの場合
        if reply.content.lower() == 'キャンセル':
            await ctx.send("✅ 日記作成をキャンセルしました。")
            return
        
        # 受け取った内容で日記を作成
        success, result = await save_message_to_github(
            reply,
            ctx.author.display_name,
            ctx.channel.name,
            content=reply.content
        )
        
        if success:
            await ctx.send(f"✅ 新しい日記を作成しました: `{result}`")
        else:
            await ctx.send(f"❌ エラー: {result}")
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ タイムアウトしました。日記の作成をキャンセルします。")

@commands.command(name='update', aliases=['u'])
async def update_entry(ctx, file_path=None, *, new_content=None):
    """日記エントリを更新するコマンド（インタラクティブ）"""
    # 許可されたチャンネルかチェック
    if ctx.channel.id not in BOT_CONFIG["ALLOWED_CHANNELS"]:
        await ctx.send("❌ このチャンネルでは日記を更新できません。")
        return
    
    # ファイルパスが指定されていない場合、今日の日記を取得
    if file_path is None:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        success, entries = await get_diary_entries(today)
        
        if not success or not entries:
            await ctx.send(f"📆 今日の日記エントリはありません。`!new`コマンドで新しく作成してください。")
            return
        
        # 1日1エントリ想定なので最初のエントリを使用
        file_path = entries[0]['path']
    
    # 新しい内容が指定されていない場合、インタラクティブモード
    if new_content is None:
        # まずファイルの内容を取得
        try:
            # GitHub APIを使用して特定のファイルを取得
            from src.utils.github_utils import get_file_content
            success, content = await get_file_content(file_path)
            
            if not success:
                await ctx.send(f"❌ ファイルの取得に失敗しました: {content}")
                return
            
            # 内容セクションを抽出
            diary_content = ""
            content_section = False
            
            for line in content.split('\n'):
                if line.startswith('## 内容'):
                    content_section = True
                    continue
                elif content_section and line.startswith('##'):
                    break
                elif content_section:
                    diary_content += line + '\n'
            
            diary_content = diary_content.strip()
            
            # 現在の内容を表示
            update_msg = await ctx.send(f"更新対象: `{file_path}`\n\n現在の日記内容：\n```\n{diary_content}\n```\n\n新しい内容を返信してください。キャンセルするには「キャンセル」と入力してください。")
            
            # 返信を待つ
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and (
                    m.reference is not None and m.reference.message_id == update_msg.id
                )
            
            try:
                # 5分間返信を待つ
                reply = await ctx.bot.wait_for('message', check=check, timeout=300.0)
                
                # キャンセルの場合
                if reply.content.lower() == 'キャンセル':
                    await ctx.send("✅ 更新をキャンセルしました。")
                    return
                
                # 内容を更新
                new_content = reply.content
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ タイムアウトしました。更新をキャンセルします。")
                return
                
        except Exception as e:
            await ctx.send(f"❌ エラー: {e}")
            return
    
    # 内容を更新
    success, result = await update_diary_entry(file_path, new_content)
    
    if success:
        await ctx.send(f"✅ 日記を更新しました: `{result}`")
    else:
        await ctx.send(f"❌ エラー: {result}")

@commands.command(name='delete', aliases=['d'])
async def delete_entry(ctx, file_path=None):
    """日記エントリを削除するコマンド（インタラクティブ）"""
    # 許可されたチャンネルかチェック
    if ctx.channel.id not in BOT_CONFIG["ALLOWED_CHANNELS"]:
        await ctx.send("❌ このチャンネルでは日記を削除できません。")
        return
    
    # ファイルパスが指定されていない場合、今日の日記を取得
    if file_path is None:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        success, entries = await get_diary_entries(today)
        
        if not success or not entries:
            await ctx.send(f"📆 今日の日記エントリはありません。")
            return
        
        # 1日1エントリ想定なので最初のエントリを使用
        file_path = entries[0]['path']
    
    # 確認メッセージ
    confirm_msg = await ctx.send(f"⚠️ 以下の日記を削除しますか？\nファイル: `{file_path}`\n\n削除するには「削除」と返信してください。キャンセルするには「キャンセル」と入力してください。")
    
    # 返信を待つ
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['削除', 'キャンセル']
    
    try:
        # 30秒間返信を待つ
        reply = await ctx.bot.wait_for('message', check=check, timeout=30.0)
        
        if reply.content.lower() == '削除':
            # 削除を実行
            success, result = await delete_diary_entry(file_path)
            
            if success:
                await ctx.send("✅ 日記を削除しました。")
            else:
                await ctx.send(f"❌ 削除エラー: {result}")
        else:
            await ctx.send("🚫 削除をキャンセルしました。")
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ タイムアウトしました。削除をキャンセルします。")
