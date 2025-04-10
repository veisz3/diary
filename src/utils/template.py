import datetime

# 日記のテンプレート定義
DIARY_TEMPLATE = """# {author}の日記エントリ

## 日時
{datetime}

## チャンネル
{channel}

## 今日の気分
(ここに気分を書いてください)

## 今日やったこと
(ここに今日やったことを書いてください)

## 明日の予定
(ここに明日の予定を書いてください)

## 感想・反省
(ここに感想や反省を書いてください)
"""

def get_template(author, channel):
    """テンプレートに値を埋め込んで返す"""
    now = datetime.datetime.now()
    return DIARY_TEMPLATE.format(
        author=author,
        datetime=now.strftime('%Y年%m月%d日 %H:%M:%S'),
        channel=channel
    )

def get_simple_template():
    """シンプルなテンプレートを返す（ヘルプ表示用）"""
    return """# 今日の気分
(ここに気分を書いてください)

# 今日やったこと
(ここに今日やったことを書いてください)

# 明日の予定
(ここに明日の予定を書いてください)

# 感想・反省
(ここに感想や反省を書いてください)
"""