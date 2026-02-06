## -*- coding: utf-8 -*-
import os, json, logging
from datetime import datetime
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise RuntimeError("Missing env vars: LINE_CHANNEL_ACCESS_TOKEN / LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUPONS_PATH = os.path.join(BASE_DIR, "data", "coupons.json")
EVENTS_PATH  = os.path.join(BASE_DIR, "data", "events.json")

def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.exception(f"JSON load failed: {path} err={e}")
        return default

def load_coupons():
    return _load_json(COUPONS_PATH, [])

def load_events():
    return _load_json(EVENTS_PATH, [])

def normalize_text(s: str) -> str:
    if not s:
        return ""
    # 全角スペース→半角、前後空白除去
    s = s.replace("　", " ").strip()
    # よくある揺れ（必要なら増やせる）
    s = s.replace("イベント情報 ", "イベント情報").strip()
    return s

def format_coupon_list(coupons):
    if not coupons:
        return "いま登録されているクーポンはありません。"
    lines = ["【クーポン一覧】"]
    for i, c in enumerate(coupons, start=1):
        lines.append(f"\n{i}. {c.get('title','（無題）')}")
        if c.get("desc"): lines.append(f"   {c['desc']}")
        if c.get("code"): lines.append(f"   コード: {c['code']}")
        if c.get("expires"): lines.append(f"   期限: {c['expires']}")
    return "\n".join(lines)

def format_event_list(events):
    if not events:
        return "いま登録されているイベント情報はありません。"
    lines = ["【イベント情報】"]
    for i, e in enumerate(events, start=1):
        lines.append(f"\n{i}. {e.get('title','（無題）')}")
        if e.get("date"): lines.append(f"   日時: {e['date']}")
        if e.get("place"): lines.append(f"   場所: {e['place']}")
        if e.get("desc"): lines.append(f"   内容: {e['desc']}")
        if e.get("url"): lines.append(f"   詳細: {e['url']}")
    return "\n".join(lines)

def help_text():
    return "「クーポン」または「イベント情報」と送ってね。"

@app.get("/")
def health():
    return "OK"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    logging.info("=== /callback called ===")
    logging.info(f"signature exists={bool(signature)} body_len={len(body)}")
    # bodyを全部出すとログがうるさいので長さだけ

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logging.exception("InvalidSignatureError: channel secret mismatch or wrong endpoint")
        abort(400)
    except Exception as e:
        logging.exception(f"Handler error: {e}")
        abort(500)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    raw = event.message.text
    text = normalize_text(raw)

    logging.info(f"Received text: raw='{raw}' normalized='{text}'")

    if text == "クーポン":
        msg = format_coupon_list(load_coupons())
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text in ("イベント情報", "イベント"):
        msg = format_event_list(load_events())
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_text()))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
