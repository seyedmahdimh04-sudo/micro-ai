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
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Init Warning: {e}")

DB_NAME = "micro_database.db"

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            question TEXT,
            answer TEXT,
            verdict TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_total_users() -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    return total

def save_feedback(user_id: str, username: str, question: str, answer: str, verdict: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback (user_id, username, question, answer, verdict) VALUES (?, ?, ?, ?, ?)",
        (str(user_id), username, question, answer, verdict)
    )
    conn.commit()
    conn.close()

def get_all_feedback(limit: int = 200):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT username, question, answer, verdict, created_at FROM feedback ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [
        {"username": r[0], "question": r[1], "answer": r[2], "verdict": r[3], "created_at": r[4]}
        for r in rows
    ]

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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT has_channel_bonus FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if row and row[0] == 0:
        c.execute("UPDATE users SET coins = coins + 25, has_channel_bonus = 1 WHERE user_id = ?", (str(user_id),))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_daily_micro_greeting(user_name: str = "کاربر") -> str:
    weekday = datetime.date.today().weekday()
    name = user_name if user_name else "دوست من"
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

def answer_question(question: str, user_name: str = None, history: list = None):
    """
    خروجی: (متن_پاسخ, وضعیت_موفقیت_بولین)
    """
    if not GEMINI_API_KEY or not client:
        return "⚠️ کلید GEMINI_API_KEY تنظیم نشده یا اتصال برقرار نیست.", False

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
        # اگه یه مدل به هر دلیلی در دسترس نبود (منسوخ شد و غیره)، خودکار مدل بعدی رو امتحان کن
        candidate_models = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]
        last_error = None
        response = None
        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    )
                )
                break
            except Exception as inner_e:
                last_error = inner_e
                continue

        if response is None:
            raise last_error if last_error else RuntimeError("هیچ مدلی در دسترس نبود")
        return response.text, True
    except Exception as e:
        err_msg = str(e)
        if "403" in err_msg or "location" in err_msg.lower() or "blocked" in err_msg.lower():
            return "⚠️ خطای دسترسی جغرافیایی به سرور جمینای. روی هاست سرور خارجی (مثل رندر) بدون مشکل اجرا می‌شود.", False
        return f"⚠️ خطای موقت در دریافت پاسخ: {err_msg}", False