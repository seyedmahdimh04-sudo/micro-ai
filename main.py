"""
اسکلت اصلی هوش مصنوعی میکرو: مدیریت دیتابیس کاربران، سکه‌ها، تاریخچه گفتگوها و بازخورد
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT DEFAULT 'گفتگوی جدید',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            question TEXT,
            answer TEXT,
            had_image INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()


# ---------------------------------------------------------------------------
# کاربران و سکه‌ها
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# تاریخچه‌ی گفتگوها (چند چت جدا برای هر کاربر، مثل ChatGPT/Gemini)
# ---------------------------------------------------------------------------
def create_conversation(user_id: str, title: str = "گفتگوی جدید") -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, title) VALUES (?, ?)", (str(user_id), title))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def list_conversations(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT id, title, created_at FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT 30",
        (str(user_id),)
    )
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]


def conversation_belongs_to(conversation_id: int, user_id: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM conversations WHERE id = ?", (conversation_id,))
    row = c.fetchone()
    conn.close()
    return bool(row) and str(row[0]) == str(user_id)


def get_turns(conversation_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT question, answer, had_image FROM turns WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"q": r[0], "a": r[1], "had_image": bool(r[2])} for r in rows]


def add_turn(conversation_id: int, question: str, answer: str, had_image: bool = False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO turns (conversation_id, question, answer, had_image) VALUES (?, ?, ?, ?)",
        (conversation_id, question, answer, int(had_image))
    )
    # اگه اولین پیامه، عنوان چت رو خودکار از روی همون سؤال بساز
    c.execute("SELECT COUNT(*) FROM turns WHERE conversation_id = ?", (conversation_id,))
    count = c.fetchone()[0]
    if count == 1:
        short_title = (question[:28] + "…") if len(question) > 28 else question
        if short_title.strip():
            c.execute("UPDATE conversations SET title = ? WHERE id = ?", (short_title, conversation_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# شخصیت میکرو و ارتباط با جمینای
# ---------------------------------------------------------------------------
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


def answer_question(question: str, user_name: str = None, history: list = None,
                     image_bytes: bytes = None, image_mime: str = None):
    """
    خروجی: (متن_پاسخ, وضعیت_موفقیت_بولین)
    history: لیستی از {"q":..., "a":...} برای حفظ تداوم گفتگو
    image_bytes/image_mime: در صورت آپلود تصویر توسط کاربر (تحلیل تصویر با جمینای)
    """
    if not GEMINI_API_KEY or not client:
        return "⚠️ کلید GEMINI_API_KEY تنظیم نشده یا اتصال برقرار نیست.", False

    try:
        contents = []
        if history:
            for turn in history[-8:]:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn.get("q", ""))]))
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=turn.get("a", ""))]))

        # ساخت پیام کاربر (متن + عکس در صورت وجود)
        user_parts = []
        if image_bytes:
            try:
                user_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime or "image/jpeg"))
            except Exception:
                pass
        user_parts.append(types.Part.from_text(text=question or "این تصویر رو برام توضیح بده"))
        contents.append(types.Content(role="user", parts=user_parts))

        # قانون سلام: فقط دفعه‌ی اول گفتگو، نه هر پیام
        is_first_turn = not history
        greeting_rule = (
            "این اولین پیام این گفتگوست؛ می‌توانی با یک سلام کوتاه و گرم شروع کنی."
            if is_first_turn else
            "این ادامه‌ی یک گفتگوی در حال انجام است؛ به هیچ‌وجه دوباره سلام یا احوال‌پرسی نکن "
            "(نگو «سلام»، «حالت چطوره» و مشابه آن)، مستقیم و بدون مقدمه برو سراغ جواب دادن."
        )

        system_instruction = f"""
تو «میکرو» هستی؛ یک دستیار هوش مصنوعی فارسی، پیشرفته و دقیق متعلق به persian_ai.
نام کاربر: {user_name or 'دوست من'}.
{greeting_rule}
اگر کاربر تصویری فرستاده، آن را با دقت تحلیل کن و درباره‌اش توضیح بده یا به سؤالش پاسخ بده.
پاسخ‌ها را کامل، ساختاریافته و با لحنی گرم و دوستانه به زبان فارسی ارائه بده.
"""
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
