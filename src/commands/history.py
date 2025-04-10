import discord
from discord.ext import commands
import datetime
import asyncio
from src.utils.github_utils import get_diary_entries, get_all_diary_entries, get_diary_by_date_range, search_diary_entries
from src.config import BOT_CONFIG

class DiaryView(discord.ui.View):
    def __init__(self, file_path):
        super().__init__(timeout=180)  # 3分のタイムアウト
        self.file_path = file_path
        
        # 更新ボタン
        update_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="更新",
            custom_id=f"update_{file_path}"
        )
        update_button.callback = self.update_callback
        
        # 削除ボタン
        delete_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="削除",
            custom_id=f"delete_{file_path}"
        )
        delete_button.callback = self.delete_callback
        
        # ボタンを追加
        self.add_item(update_button)
        self.add_item(delete_button)
    
    async def update_callback(self, interaction):
        # インタラクションをすぐに確認
        await interaction.response.send_message("日記を更新します。新しい内容を入力してください。キャンセルする場合は「キャンセル」と入力してください。", ephemeral=True)
        
        # 元のメッセージのチャンネルを取得
        channel = interaction.channel
        
        # ファイルの内容を取得
        from src.utils.github_utils import get_file_content
        success, content = await get_file_content(self.file_path)
        
        if not success:
            await interaction.followup.send(f"ファイルの取得に失敗しました: {content}", ephemeral=True)
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
        update_msg = await channel.send(f"更新対象: `{self.file_path}`\n\n現在の日記内容：\n```\n{diary_content}\n```\n\n新しい内容を返信してください。キャンセルするには「キャンセル」と入力してください。")
        
        # 待機するユーザーを指定
        user_id = interaction.user.id
        
        # 返信を待つ
        def check(m):
            return m.author.id == user_id and m.channel == channel and (
                m.reference is not None and m.reference.message_id == update_msg.id
            )
        
        try:
            # 5分間返信を待つ
            bot = interaction.client
            reply = await bot.wait_for('message', check=check, timeout=300.0)
            
            # キャンセルの場合
            if reply.content.lower() == 'キャンセル':
                await channel.send("✅ 更新をキャンセルしました。", reference=update_msg)
                return
            
            # 内容を更新
            from src.utils.github_utils import update_diary_entry
            success, result = await update_diary_entry(self.file_path, reply.content)
            
            if success:
                await channel.send(f"✅ 日記を更新しました: `{result}`", reference=update_msg)
            else:
                await channel.send(f"❌ エラー: {result}", reference=update_msg)
                
        except asyncio.TimeoutError:
            await channel.send("⏰ タイムアウトしました。更新をキャンセルします。", reference=update_msg)
    
    async def delete_callback(self, interaction):
        # 削除確認メッセージを表示
        view = DeleteConfirmView(self.file_path)
        await interaction.response.send_message(
            f"⚠️ 本当に `{self.file_path}` を削除しますか？",
            view=view,
            ephemeral=True
        )

class DeleteConfirmView(discord.ui.View):
    def __init__(self, file_path):
        super().__init__(timeout=60)  # 1分のタイムアウト
        self.file_path = file_path
    
    @discord.ui.button(label="削除する", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction, button):
        # ファイルを削除
        from src.utils.github_utils import delete_diary_entry
        success, result = await delete_diary_entry(self.file_path)
        
        if success:
            await interaction.response.edit_message(content=f"✅ 日記を削除しました: `{self.file_path}`", view=None)
            
            # 元のメッセージにも通知
            try:
                await interaction.channel.send(f"✅ {interaction.user.display_name}さんが日記を削除しました: `{self.file_path}`")
            except:
                pass
        else:
            await interaction.response.edit_message(content=f"❌ 削除エラー: {result}", view=None)
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction, button):
        await interaction.response.edit_message(content="🚫 削除をキャンセルしました。", view=None)
    
    async def on_timeout(self):
        # タイムアウト時の処理
        for item in self.children:
            item.disabled = True
        
        try:
            # メッセージがまだ存在している場合は更新
            if hasattr(self, "message"):
                await self.message.edit(content="⏰ タイムアウトしました。削除をキャンセルします。", view=self)
        except:
            pass

@commands.command(name='history', aliases=['h'])
async def get_history(ctx, date_arg='0'):
    """日記履歴を表示するコマンド
    引数:
        date_arg (str): 
            - 数字: 相対日数（0=今日, 1=昨日, ...）
            - 日付: YYYY-MM-DD形式
            - 'all': すべての日記一覧
    """
    try:
        if date_arg.lower() == 'all':
            # 全ての日記を表示
            await show_all_entries(ctx)
            return
        
        # 日付の処理
        if date_arg.isdigit() or (date_arg[0] == '-' and date_arg[1:].isdigit()):
            # 相対日数の場合
            days_offset = int(date_arg)
            target_date = (datetime.datetime.now() - datetime.timedelta(days=abs(days_offset))).strftime('%Y-%m-%d')
        else:
            # 日付形式のバリデーション
            try:
                datetime.datetime.strptime(date_arg, '%Y-%m-%d')
                target_date = date_arg
            except ValueError:
                await ctx.send("❌ 日付の形式が正しくありません。`YYYY-MM-DD`形式か、相対日数（0: 今日, 1: 昨日）、または 'all' を指定してください。")
                return
        
        # 日記エントリ取得
        success, entries = await get_diary_entries(target_date)
        
        if not success or not entries:
            await ctx.send(f"📆 {target_date} の日記エントリはありません。")
            return
        
        # エントリが多い場合は分割して送信
        for i, entry in enumerate(entries):
            embed = discord.Embed(
                title=f"📔 日記エントリ {i+1}/{len(entries)}",
                description=f"**{target_date}** の記録",
                color=0x3498db
            )
            
            # コンテンツから情報を抽出（簡易パース）
            lines = entry['content'].split('\n')
            author = "不明"
            sections = {}
            current_section = None
            
            for line in lines:
                if line.startswith('# ') and '日記エントリ' in line:
                    author = line.replace('# ', '').replace('の日記エントリ', '')
                elif line.startswith('## '):
                    current_section = line[3:]
                    sections[current_section] = ""
                elif current_section:
                    sections[current_section] += line + '\n'
            
            embed.add_field(name="投稿者", value=author, inline=True)
            embed.add_field(name="ファイル", value=entry['filename'], inline=True)
            
            # 各セクションを埋め込みに追加
            for section, content in sections.items():
                if section != "日時" and section != "チャンネル" and content.strip():
                    # 内容が長い場合は切り詰める
                    if len(content) > 1024:
                        content = content[:1021] + '...'
                    
                    embed.add_field(name=section, value=content.strip() or "内容なし", inline=False)
            
            # ここでViewを追加
            view = DiaryView(entry['path'])
            
            await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"❌ エラー: {e}")

async def show_all_entries(ctx):
    """すべての日記エントリを一覧表示"""
    # すべての日記エントリを取得
    success, all_entries = await get_all_diary_entries()
    
    if not success or not all_entries:
        await ctx.send("📆 日記エントリはありません。")
        return
    
    # 日付ごとにグループ化
    entries_by_date = {}
    for entry in all_entries:
        date = entry['date']
        if date not in entries_by_date:
            entries_by_date[date] = []
        entries_by_date[date].append(entry)
    
    # 日付順に並べ替え（新しい順）
    sorted_dates = sorted(entries_by_date.keys(), reverse=True)
    
    # 一覧を表示
    embed = discord.Embed(
        title="📚 日記一覧",
        description=f"合計 {len(all_entries)} 件の日記があります。詳細を見るには日付をクリックしてください。",
        color=0x3498db
    )
    
    for date in sorted_dates[:25]:  # 最新25日分だけ表示
        count = len(entries_by_date[date])
        embed.add_field(
            name=f"{date} ({count}件)",
            value=f"`!h {date}` で詳細表示",
            inline=True
        )
    
    if len(sorted_dates) > 25:
        embed.set_footer(text=f"他 {len(sorted_dates) - 25} 日分の日記があります")
    
    await ctx.send(embed=embed)

@commands.command(name='today', aliases=['t'])
async def today_entry(ctx):
    """今日の日記を表示するシンプルなコマンド"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    success, entries = await get_diary_entries(today)
    
    if not success or not entries:
        await ctx.send(f"📆 今日はまだ日記が書かれていません。`!new`コマンドで日記を書きましょう。")
        return
    
    # 1人1日1件なので最初のエントリを表示
    entry = entries[0]
    
    embed = discord.Embed(
        title=f"📔 今日の日記",
        description=f"**{today}**",
        color=0x3498db
    )
    
    # 内容のセクションを抽出
    sections = {}
    current_section = None
    
    for line in entry['content'].split('\n'):
        if line.startswith('## '):
            current_section = line[3:]
            sections[current_section] = ""
        elif current_section:
            sections[current_section] += line + '\n'
    
    # 各セクションを埋め込みに追加
    for section, content in sections.items():
        if section != "日時" and section != "チャンネル" and content.strip():  # メタデータは除外
            if len(content) > 1024:
                content = content[:1021] + '...'
            
            embed.add_field(name=section, value=content.strip(), inline=False)
    
    # ここでViewを追加
    view = DiaryView(entry['path'])
    
    embed.set_footer(text=f"ファイル: {entry['filename']}")
    await ctx.send(embed=embed, view=view)

@commands.command(name='search', aliases=['s'])
async def search_entries(ctx, *, keyword):
    """日記エントリをキーワードで検索するコマンド"""
    if not keyword:
        await ctx.send("❌ 検索キーワードを入力してください。")
        return
    
    await ctx.send(f"🔍 「{keyword}」で検索中...")
    
    # 検索を実行
    success, results = await search_diary_entries(keyword)
    
    if not success or not results:
        await ctx.send(f"❌ キーワード「{keyword}」を含む日記は見つかりませんでした。")
        return
    
    # 検索結果を表示
    embed = discord.Embed(
        title=f"🔍 検索結果: {keyword}",
        description=f"{len(results)} 件の日記が見つかりました",
        color=0x3498db
    )
    
    # 最新の5件だけ詳細表示
    for i, entry in enumerate(results[:5]):
        date = entry['date']
        
        # コンテキストを抽出（キーワードを含む部分の前後の文章）
        content = entry['content'].lower()
        keyword_pos = content.find(keyword.lower())
        
        if keyword_pos != -1:
            start = max(0, keyword_pos - 50)
            end = min(len(content), keyword_pos + len(keyword) + 50)
            
            # コンテキストの整形
            context = "..." if start > 0 else ""
            context += content[start:end].replace(keyword.lower(), f"**{keyword.lower()}**")
            context += "..." if end < len(content) else ""
            
            embed.add_field(
                name=f"{date}",
                value=context,
                inline=False
            )
    
    if len(results) > 5:
        embed.set_footer(text=f"他 {len(results) - 5} 件の結果があります")
    
    await ctx.send(embed=embed)
