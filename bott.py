"""
ربات رسمی بله «میکرو» با حل باگ دکمه‌ها و محافظت از سکه
اجرا: python bott.py
"""

import os
import time
import requests
from dotenv import load_dotenv
from main import (
    answer_question, get_or_create_user, get_user_coins,
    add_user_coins, deduct_user_coins, get_daily_micro_greeting,
    claim_channel_bonus
)

load_dotenv(encoding="utf-8-sig")

BALE_TOKEN = os.getenv("BALE_BOT_TOKEN")
PROVIDER_TOKEN = os.getenv("BALE_PAYMENT_PROVIDER_TOKEN", "WALLET-TEST-1111111111111111")
ADMIN_UID = os.getenv("ADMIN_UID", "admin_persian_ai")
CHANNEL_LINK = "https://ble.ir/persian_ai"
BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

COIN_PACKAGES = {
    "pack_40":  {"coins": 40,  "price": 200000,  "title": "🪙 بسته ۴۰ سکه (استارتر)", "desc": "۴۰ سکه میکرو برای چت و ساخت تصویر"},
    "pack_70":  {"coins": 70,  "price": 700000,  "title": "🪙 بسته ۷۰ سکه (استارتر)", "desc": "۷۰ سکه میکرو برای استفاده مداوم"},
    "pack_100": {"coins": 100, "price": 800000,  "title": "🪙 بسته ۱۰۰ سکه (ویژه 🔥)", "desc": "۱۰۰ سکه میکرو با تخفیف ویژه"},
    "pack_200": {"coins": 200, "price": 2000000, "title": "🪙 بسته ۲۰۰ سکه (پرمیوم)", "desc": "۲۰۰ سکه میکرو پرمیوم"},
    "pack_400": {"coins": 400, "price": 3000000, "title": "🪙 بسته ۴۰۰ سکه (افسانه‌ای 👑)", "desc": "۴۰۰ سکه میکرو افسانه‌ای"},
}

user_states = {}
user_histories = {}

def call_api(method: str, payload: dict):
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=payload, timeout=20)
        return r.json()
    except Exception as e:
        print(f"API Error ({method}): {e}")
        return {}

def send_main_menu(chat_id: int, user_name: str):
    coins = get_user_coins(str(chat_id))
    greeting = get_daily_micro_greeting(user_name)
    text = (
        f"🤖 {greeting}\n\n"
        f"🪙 موجودی سکه شما: {coins}\n"
        "✨ عضویت در کانال میکرو = ۳۰ سکه رایگان\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    keyboard = {
        "keyboard": [
            [{"text": "💬 ارتباط با میکرو"}, {"text": "🪙 افزایش اعتبار و خرید سکه"}],
            [{"text": "📢 عضویت در کانال (+۳۰ سکه)"}, {"text": "👨‍💻 پشتیبانی"}]
        ],
        "resize_keyboard": True
    }
    call_api("sendMessage", {"chat_id": chat_id, "text": text, "reply_markup": keyboard})

def send_invoice_packages(chat_id: int):
    inline_keyboard = []
    for key, data in COIN_PACKAGES.items():
        toman = data["price"] // 10
        inline_keyboard.append([{"text": f"{data['title']} — {toman:,} تومان", "callback_data": key}])
    
    keyboard = {"inline_keyboard": inline_keyboard}
    call_api("sendMessage", {
        "chat_id": chat_id,
        "text": "🛒 لطفاً بسته سکه مورد نظر خود را انتخاب کنید:\n(پرداخت آنی از طریق کیف‌پول بله)",
        "reply_markup": keyboard
    })

def send_bale_invoice(chat_id: int, pack_key: str):
    pack = COIN_PACKAGES.get(pack_key)
    if not pack: return
    
    payload = {
        "chat_id": chat_id,
        "title": pack["title"],
        "description": pack["desc"],
        "payload": f"{chat_id}:{pack_key}",
        "provider_token": PROVIDER_TOKEN,
        "prices": [{"label": pack["title"], "amount": pack["price"]}],
    }
    call_api("sendInvoice", payload)

def run_bot():
    offset = 0
    print("🚀 ربات بله میکرو روشن شد...")
    while True:
        try:
            updates = call_api("getUpdates", {"offset": offset, "timeout": 25})
            if not updates.get("ok"):
                time.sleep(2)
                continue

            for u in updates.get("result", []):
                offset = u["update_id"] + 1

                if "pre_checkout_query" in u:
                    pq = u["pre_checkout_query"]
                    call_api("answerPreCheckoutQuery", {
                        "pre_checkout_query_id": pq["id"],
                        "ok": True
                    })
                    continue

                if "callback_query" in u:
                    cq = u["callback_query"]
                    data = cq.get("data")
                    chat_id = cq["from"]["id"]
                    if data in COIN_PACKAGES:
                        send_bale_invoice(chat_id, data)
                    continue

                msg = u.get("message")
                if not msg: continue

                chat_id = msg["chat"]["id"]
                user_id = str(chat_id)
                user_name = msg["from"].get("first_name", "کاربر")
                get_or_create_user(user_id, user_name)

                if "successful_payment" in msg:
                    sp = msg["successful_payment"]
                    inv_payload = sp.get("invoice_payload", "")
                    if ":" in inv_payload:
                        _, pack_key = inv_payload.split(":", 1)
                        if pack_key in COIN_PACKAGES:
                            added = COIN_PACKAGES[pack_key]["coins"]
                            add_user_coins(user_id, added)
                            call_api("sendMessage", {
                                "chat_id": chat_id,
                                "text": f"🎉 پرداخت شما با موفقیت تایید شد!\n🪙 {added} سکه به موجودی شما اضافه گردید."
                            })
                            send_main_menu(chat_id, user_name)
                    continue

                text = msg.get("text", "").strip()

                if text == "/start":
                    user_states[chat_id] = "normal"
                    send_main_menu(chat_id, user_name)
                    continue

                if text == "📢 عضویت در کانال (+۳۰ سکه)":
                    got_bonus = claim_channel_bonus(user_id)
                    if got_bonus:
                        call_api("sendMessage", {
                            "chat_id": chat_id,
                            "text": f"🎉 عالی! ۳۰ سکه به موجودی شما اضافه شد.\nبرای عضویت در کانال (اگه هنوز عضو نیستی) اینجا بزن:\n{CHANNEL_LINK}"
                        })
                        send_main_menu(chat_id, user_name)
                    else:
                        call_api("sendMessage", {
                            "chat_id": chat_id,
                            "text": f"شما قبلاً این پاداش رو دریافت کردید 😊\nکانال: {CHANNEL_LINK}"
                        })
                    continue

                if text == "🪙 افزایش اعتبار و خرید سکه":
                    send_invoice_packages(chat_id)
                    continue

                if text == "👨‍💻 پشتیبانی":
                    call_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": f"💬 شناسه کاربری شما (UID): `{user_id}`\nجهت ارتباط با پشتیبانی به آی‌دی زیر پیام دهید:\n@admin_persian_ai"
                    })
                    continue

                if text == "💬 ارتباط با میکرو":
                    user_states[chat_id] = "chatting"
                    call_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": "🤖 حالت گفتگو با میکرو فعال شد! سوال خود را بپرسید:"
                    })
                    continue

                if user_states.get(chat_id) == "chatting" or not text.startswith("/"):
                    current_coins = get_user_coins(user_id)
                    if current_coins >= 5:
                        hist = user_histories.get(chat_id, [])
                        ans, success = answer_question(text, user_name, hist)
                        
                        if success:
                            deduct_user_coins(user_id, 5)
                            hist.append({"q": text, "a": ans})
                            user_histories[chat_id] = hist[-10:]
                            rem = get_user_coins(user_id)
                            call_api("sendMessage", {
                                "chat_id": chat_id,
                                "text": f"{ans}\n\n─────────────\n🪙 ۵ سکه کسر شد (باقی‌مانده: {rem})"
                            })
                        else:
                            call_api("sendMessage", {
                                "chat_id": chat_id,
                                "text": f"{ans}\n(هیچ سکه‌ای از حساب شما کسر نشد)"
                            })
                    else:
                        call_api("sendMessage", {
                            "chat_id": chat_id,
                            "text": "⚠️ سکه شما برای گفتگو کافی نیست. لطفاً از بخش «افزایش اعتبار» سکه تهیه کنید."
                        })

        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run_bot()