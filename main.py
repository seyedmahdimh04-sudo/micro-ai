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
    # جدول کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 20,
            has_channel_bonus INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # جدول بازخوردها (لایک و دیس‌لایک) برای پنل ادمین
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            question TEXT,
            answer TEXT,
            feedback_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def set_user_name(user_id: str, username: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, str(user_id)))
    conn.commit()
    conn.close()

def get_or_create_user(user_id: str, username: str = ""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, username, coins, has_channel_bonus FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    if not row:
        # کاربری که تازه وارد شده اسمش خالیه تا Onboarding بهش نشون داده بشه
        c.execute("INSERT INTO users (user_id, username, coins) VALUES (?, ?, 20)", (str(user_id), username))
        conn.commit()
        db_username, coins, bonus = username, 20, 0
    else:
        db_username, coins, bonus = row[1], row[2], row[3]
    conn.close()
    return {"user_id": str(user_id), "username": db_username, "coins": coins, "has_channel_bonus": bool(bonus)}

def get_user_coins(user_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (str(user_id),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 20

def deduct_user_coins(user_id: str, amount: int) -> bool:
    # امیرمهدی (ادمین) سکه نامحدود داره و ازش کم نمیشه!
    if str(user_id) == "admin_persian_ai":
        return True
        
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

def save_feedback(user_id: str, question: str, answer: str, feedback_type: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO feedbacks (user_id, question, answer, feedback_type) VALUES (?, ?, ?, ?)",
              (str(user_id), question, answer, feedback_type))
    conn.commit()
    conn.close()

def get_admin_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT user_id, question, feedback_type, created_at FROM feedbacks ORDER BY created_at DESC LIMIT 50")
    recent_feedbacks = [{"uid": r[0], "q": r[1], "type": r[2], "date": r[3]} for r in c.fetchall()]
    conn.close()
    
    return {"total_users": total_users, "feedbacks": recent_feedbacks}

def answer_question_stream(question: str, user_name: str = None, history: list = None):
    """
    این تابع حالا به جای یک متن کامل، کلمات را تکه تکه (Stream) برمی‌گرداند.
    """
    if not GEMINI_API_KEY or not client:
        yield "⚠️ کلید متصل نیست."
        return

    try:
        contents = []
        if history:
            for turn in history[-8:]:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn.get("q", ""))]))
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=turn.get("a", ""))]))
        
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))

        system_instruction = f"""
تو «رایکا» (Raika) هستی؛ یک دستیار هوش مصنوعی فارسی، پیشرفته، دوست‌داشتنی و متعلق به persian_ai.
نام کاربر: {user_name or 'دوست من'}.
پاسخ‌ها را کامل، ساختاریافته و با لحنی گرم و دوستانه به زبان فارسی ارائه بده. از ایموجی‌های جذاب استفاده کن.
"""
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash-lite", # یا مدل دلخواهت
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        
        for chunk in response_stream:
            yield chunk.text

    except Exception as e:
        yield f"⚠️ خطای موقت در دریافت پاسخ: {str(e)}"