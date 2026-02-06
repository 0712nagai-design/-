# -*- coding: utf-8 -*-
import os, json
from datetime import datetime
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ======================
# 環境変数（Render等で設定）
# ======================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise RuntimeError("Missing env vars: LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)

# ======================
# データ読み込み（JSONファイル）
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUPONS_PATH = os.path.join(BASE_DIR, "data", "coupons.json")
EVENTS_PATH  = os.path.join(BASE_DIR, "data", "events.json")

def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception:
        return default

def load_coupons():
    # list 形式を想定
    return _load_json(COUPONS_PATH, [])

def load_events():
    # list 形式を想定
    return _load_json(EVENTS_PATH, [])

# ======================
# 表示用フォーマット
# ======================
def format_coupon_list(coupons):
    if not coupons:
        return "いま登録されているクーポンはありません。"

    lines = ["【クーポン一覧】"]
    now = datetime.now().date()

    for i, c in enumerate(coupons, start=1):
        title = c.get("title", "（無題）")
        desc = c.get("desc", "")
        code = c.get("code", "")
        expires = c.get("expires", "")  # "YYYY-MM-DD" 推奨
        note = c.get("note", "")

        # 期限表示をちょい丁寧に
        exp_text = f"期限: {expires}" if expires else "期限: 設定なし"
        if expires:
            try:
                exp_date = datetime.strptime(expires, "%Y-%m-%d").date()
                if exp_date < now:
                    exp_text += "（期限切れ）"
            except Exception:
                pass

        lines.append(f"\n{i}. {title}")
        if desc:
            lines.append(f"   {desc}")
        if code:
            lines.append(f"   コード: {code}")
        lines.append(f"   {exp_text}")
        if note:
            lines.append(f"   {note}")

    return "\n".join(lines)

def format_event_list(events):
    if not events:
        return "いま登録されているイベント情報はありません。"

    lines = ["【イベント情報】"]
    for i, e in enumerate(events, start=1):
        title = e.get("title", "（無題）")
        date = e.get("date", "")      # "YYYY-MM-DD" or "YYYY-MM-DD HH:MM" etc
        place = e.get("place", "")
        desc = e.get("desc", "")
        url = e.get("url", "")

        lines.append(f"\n{i}. {title}")
        if date:
            lines.append(f"   日時: {date}")
        if place:
            lines.append(f"   場所: {place}")
        if desc:
            lines.append(f"   内容: {desc}")
        if url:
            lines.append(f"   詳細: {url}")

    return "\n".join(lines)

def help_text():
    return (
        "使い方:\n"
        "・「クーポン」→ 登録済みクーポン一覧\n"
        "・「イベント情報」→ 登録済みイベント一覧\n"
        "（例: クーポン / イベント情報）"
    )

# ======================
# Webhook
# ======================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ======================
# メッセージ処理
# ======================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    text = (event.message.text or "").strip()

    # ゆるく揺れ吸収（全角・余計なスペース等）
    normalized = text.replace("　", " ").strip()

    if normalized == "クーポン":
        coupons = load_coupons()
        msg = format_coupon_list(coupons)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if normalized in ("イベント情報", "イベント", "event", "events"):
        events = load_events()
        msg = format_event_list(events)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    # その他
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text()))

# ======================
# ローカル起動
# ======================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
