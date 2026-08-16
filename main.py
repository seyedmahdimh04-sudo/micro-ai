"""
اسکلت اصلی هوش مصنوعی میکرو و مدیریت دیتابیس کاربران و سکه‌ها
"""

import os
import sqlite3
import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(encoding="utf-8-sig")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

DB_NAME = "micro_database.db"

# ----------------------------------------------------
# مدیریت دیتابیس مشترک بین ربات بله و وب‌سایت
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 20,
            has_channel_bonus INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_or_create_user(user_id: str, username: str = "کاربر"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, coins, has_channel_bonus FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, username, coins) VALUES (?, ?, 20)", (str(user_id), username))
        conn.commit()
        coins = 20
        bonus = 0
    else:
        coins = row[1]
        bonus = row[2]
    conn.close()
    return {"user_id": str(user_id), "coins": coins, "has_channel_bonus": bool(bonus)}

def get_user_coins(user_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 20

def add_user_coins(user_id: str, amount: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, str(user_id)))
    conn.commit()
    conn.close()

def deduct_user_coins(user_id: str, amount: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if row and row[0] >= amount:
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, str(user_id)))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def claim_channel_bonus(user_id: str) -> bool:
    """اعطای ۴۰ سکه رایگان برای عضویت در کانال"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT has_channel_bonus FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if row and row[0] == 0:
        c.execute("UPDATE users SET coins = coins + 40, has_channel_bonus = 1 WHERE user_id = ?", (str(user_id),))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ----------------------------------------------------
# تولید جملات اختصاصی هر روز هفته
# ----------------------------------------------------
def get_daily_micro_greeting(user_name: str = "کاربر") -> str:
    weekday = datetime.date.today().weekday()
    name = user_name if user_name else "دوست من"
    
    # 5=شنبه, 6=یکشنبه, 0=دوشنبه, 1=سه‌شنبه, 2=چهارشنبه, 3=پنج‌شنبه, 4=جمعه
    greetings = {
        5: f"چه چیزی خلق کنیم {name}؟",
        6: f"میکروفن دست شماست {name}!",
        0: "میکرو مشتاقانه منتظر چت با شماست!",
        1: f"چه فکری در ذهن دارید {name}؟",
        2: f"بیاید با هم فکر کنیم {name}!",
        3: "تکنولوژی در دستان شماست!",
        4: "تکنولوژی در دستان شماست!"
    }
    return greetings.get(weekday, f"امروز چه چیزی خلق کنیم {name}؟")

# ----------------------------------------------------
# پردازش پاسخ با جمینای
# ----------------------------------------------------
def answer_question(question: str, user_name: str = None, history: list = None) -> str:
    if not GEMINI_API_KEY or not client:
        return "⚠️ کلید GEMINI_API_KEY تنظیم نشده است."

    try:
        contents = []
        if history:
            for turn in history[-8:]:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn.get("q", ""))]))
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=turn.get("a", ""))]))
        
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

        system_instruction = f"""
تو «میکرو» هستی؛ یک دستیار هوش مصنوعی فارسی، پیشرفته و دقیق متعلق به persian_ai.
نام کاربر: {user_name or 'دوست من'}.
پاسخ‌ها را کامل، ساختاریافته و با لحنی گرم و دوستانه به زبان فارسی ارائه بده.
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ خطا در تولید پاسخ: {str(e)}"