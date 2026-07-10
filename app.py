"""
وب‌سایت محلی چت‌بات خبری «میکرو»
------------------------------------
این فایل یک رابط وب می‌سازد تا بتوانید از طریق مرورگر با چت‌بات صحبت کنید،
تصویر بسازید، و در صورت داشتن رمز مدیریتی، بدون محدودیت از همه‌ی ابزارها استفاده کنید.

اجرا:
    python app.py

بعد از اجرا، مرورگر را باز کنید و بروید به:
    http://127.0.0.1:5000
"""

import os
import time
import secrets
from datetime import date, timedelta
from collections import defaultdict
from flask import Flask, request, render_template_string, session, redirect, url_for
from urllib.parse import quote
from main import answer_question

app = Flask(__name__)
# کلید امن برای session (روی Render حتماً به‌عنوان متغیر محیطی SECRET_KEY تنظیمش کن)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
# مهم: session تا ۳۰ روز باقی می‌مونه، حتی اگه مرورگر بسته بشه (رفع باگ فراموشی اسم/محدودیت)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"

# رمز مخصوص سازنده برای باز کردن پنل مدیریت و رفع محدودیت‌ها.
# پیشنهاد می‌شود این مقدار را روی Render به‌عنوان متغیر محیطی ADMIN_SECRET ست کنید
# تا داخل کد عمومی گیت‌هاب دیده نشود؛ فعلاً مقدار پیش‌فرض همان رمزیه که خواستید.
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")

# محدودیت روزانه‌ی هر کاربر برای ابزار «مدل تصور» (تصویرساز رایگان)
DAILY_LIMIT_FREE_IMAGE = 5

# ---------------------------------------------------------------------------
# آمار ساده‌ی کاربران (در حافظه؛ با هر ری‌استارت سرور صفر می‌شود چون هاست رایگانه)
# ---------------------------------------------------------------------------
monthly_users = set()          # شناسه‌های یکتای کاربرانی که این ماه پیام دادند
online_users = {}              # user_id -> آخرین زمان فعالیت
image_usage = defaultdict(lambda: {"date": None, "count": 0})  # user_id -> مصرف روزانه تصویر

ONLINE_WINDOW_SECONDS = 90     # کاربر تا ۹۰ ثانیه بعد از آخرین حرکت "آنلاین" حساب می‌شود
ONLINE_LIMIT = 5               # از این تعداد کاربر آنلاین بیشتر، سرور "شلوغ" اعلام می‌شود


def get_user_id():
    """شناسه‌ی یکتا برای هر کاربر (بر اساس session)"""
    session.permanent = True  # مهم: با این کار session با بستن مرورگر پاک نمی‌شه
    if "uid" not in session:
        session["uid"] = secrets.token_hex(8)
    return session["uid"]


def track_activity():
    """ثبت بازدید کاربر برای آمار ماهانه و آنلاین"""
    uid = get_user_id()
    monthly_users.add(f"{date.today().strftime('%Y-%m')}:{uid}")
    online_users[uid] = time.time()


def count_online():
    now = time.time()
    stale = [u for u, t in online_users.items() if now - t > ONLINE_WINDOW_SECONDS]
    for u in stale:
        del online_users[u]
    return len(online_users)


def count_monthly():
    prefix = date.today().strftime('%Y-%m') + ":"
    return len([u for u in monthly_users if u.startswith(prefix)])


def is_admin() -> bool:
    return session.get("is_admin", False)


def check_daily_limit(tool_key: str, limit: int) -> bool:
    """برمی‌گرداند True اگر کاربر هنوز مجاز به استفاده باشد"""
    if is_admin():
        return True
    uid = get_user_id()
    today_str = date.today().isoformat()
    usage = image_usage[f"{tool_key}:{uid}"]
    if usage["date"] != today_str:
        usage["date"] = today_str
        usage["count"] = 0
    return usage["count"] < limit


def increment_daily_usage(tool_key: str):
    if is_admin():
        return
    uid = get_user_id()
    today_str = date.today().isoformat()
    usage = image_usage[f"{tool_key}:{uid}"]
    if usage["date"] != today_str:
        usage["date"] = today_str
        usage["count"] = 0
    usage["count"] += 1


def remaining_daily(tool_key: str, limit: int) -> int:
    if is_admin():
        return -1  # یعنی نامحدود
    uid = get_user_id()
    today_str = date.today().isoformat()
    usage = image_usage[f"{tool_key}:{uid}"]
    if usage["date"] != today_str:
        return limit
    return max(0, limit - usage["count"])


# ---------------------------------------------------------------------------
# قالب صفحه‌ی خوش‌آمدگویی (قبل از ورود به چت)
# ---------------------------------------------------------------------------
WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="میکرو، دستیار هوش مصنوعی فارسی‌زبان رایگان: اخبار روز، گفتگوی هوشمند و ساخت تصویر با هوش مصنوعی. ساخته شده توسط تیم فنی persian_ai.">
    <meta name="keywords" content="میکرو, هوش مصنوعی فارسی, چت بات فارسی, اخبار هوش مصنوعی, persian_ai, ساخت تصویر هوش مصنوعی">
    <meta property="og:title" content="{{ site_name }}">
    <meta property="og:description" content="دستیار هوش مصنوعی فارسی‌زبان رایگان برای اخبار، گفتگو و ساخت تصویر.">
    <meta property="og:type" content="website">
    <title>{{ site_name }}</title>
    <style>
        body {
            font-family: Tahoma, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e1e2f, #2a2a4a);
            color: #eee;
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .box {
            text-align: center;
            padding: 40px;
            max-width: 420px;
        }
        .box h1 { font-size: 26px; color: #7dd3fc; margin-bottom: 6px; }
        .box p { color: #999; margin-bottom: 26px; }
        input[type=text] {
            width: 100%;
            padding: 14px 18px;
            border-radius: 10px;
            border: 1px solid #444;
            background: #2a2a3d;
            color: #eee;
            font-size: 16px;
            margin-bottom: 14px;
            box-sizing: border-box;
            text-align: center;
        }
        button {
            width: 100%;
            padding: 14px;
            border-radius: 10px;
            border: none;
            background: #7dd3fc;
            color: #1e1e2f;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #5cc4f5; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🤖 {{ site_name }}</h1>
        <p>سلام! اسمت چیه؟</p>
        <form method="POST" action="/start">
            <input type="text" name="user_name" placeholder="اسمت رو بنویس..." autofocus required>
            <button type="submit">شروع گفتگو</button>
        </form>
    </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# قالب اصلی سایت (چت، تصویر، پنل مدیریت)
# ---------------------------------------------------------------------------
PAGE_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_name }}</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: Tahoma, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e1e2f, #2a2a4a);
            color: #eee;
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 20px;
            font-size: 12px;
            color: #888;
        }
        .topbar span.badge {
            background: #2a2a3d;
            padding: 4px 12px;
            border-radius: 999px;
        }
        header {
            text-align: center;
            padding: 10px 20px 10px;
        }
        header h1 {
            font-size: 28px;
            color: #7dd3fc;
            margin: 0;
        }
        header p {
            color: #999;
            font-size: 14px;
            margin-top: 8px;
        }
        .container {
            max-width: 750px;
            margin: 20px auto;
            padding: 0 20px 60px;
        }
        form.main-form {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
        }
        input[type=text] {
            flex: 1;
            padding: 14px 18px;
            border-radius: 10px;
            border: 1px solid #444;
            background: #2a2a3d;
            color: #eee;
            font-size: 16px;
        }
        button {
            padding: 14px 28px;
            border-radius: 10px;
            border: none;
            background: #7dd3fc;
            color: #1e1e2f;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { background: #5cc4f5; }
        .question {
            color: #fbbf24;
            font-size: 18px;
            margin-bottom: 16px;
        }
        .answer {
            white-space: pre-wrap;
            background: #2a2a3d;
            padding: 24px;
            border-radius: 14px;
            line-height: 1.9;
            font-size: 16px;
        }
        .error {
            background: #4a1e2a;
            color: #ffb3c0;
            padding: 16px;
            border-radius: 10px;
        }
        .limit-note {
            color: #999;
            font-size: 13px;
            margin-bottom: 14px;
        }
        footer {
            text-align: center;
            color: #666;
            font-size: 13px;
            margin-top: 40px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 10px 24px;
            border-radius: 999px;
            text-decoration: none;
            color: #ccc;
            background: #2a2a3d;
            font-size: 14px;
        }
        .tab.active {
            background: #7dd3fc;
            color: #1e1e2f;
            font-weight: bold;
        }
        .image-result { text-align: center; }
        .image-result img {
            max-width: 100%;
            border-radius: 14px;
            margin-top: 10px;
        }
        .admin-badge {
            background: #22c55e;
            color: #06210f;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: bold;
            margin-right: 6px;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <span class="badge">👥 کاربران این ماه: {{ monthly_count }}</span>
        <span class="badge">🟢 آنلاین: {{ online_count }}</span>
    </div>

    <header>
        <h1>🤖 {{ site_name }} {% if admin %}<span class="admin-badge">پنل مدیریت</span>{% endif %}</h1>
        <p>{{ ('دیگه چی می‌خوای ' + user_name + '؟ امر امرِ شماست، من آماده‌ام 👑') if admin else 'چت‌بات خبری هوشمند و ساخت تصویر با هوش مصنوعی' }}</p>
    </header>

    <div class="container">
        {% if busy %}
            <div class="error">🚦 در این لحظه سرورها شلوغ می‌باشد و امکان ارائه خدمات مقدور نیست! از صبر شما سپاسگزاریم.</div>
        {% else %}
        <div class="tabs">
            <a href="/" class="tab {{ 'active' if mode == 'chat' else '' }}">💬 پرسش و پاسخ</a>
            <a href="/image" class="tab {{ 'active' if mode == 'image' else '' }}">🖼️ مدل تصور (تصویرساز)</a>
        </div>

        {% if mode == 'chat' %}
        <form class="main-form" method="POST" action="/">
            <input type="text" name="question" placeholder="سؤال خودت رو بپرس..." value="{{ question or '' }}" autofocus required>
            <button type="submit">پرسیدن</button>
        </form>

        {% if question %}
            <div class="question">❓ {{ question }}</div>
            {% if error %}
                <div class="error">⚠️ خطا: {{ error }}</div>
            {% else %}
                <div class="answer">{{ answer }}</div>
            {% endif %}
        {% endif %}

        {% else %}
        <div class="limit-note">
            {% if admin %}
                ✨ به‌عنوان مدیر، محدودیتی برای تو وجود نداره.
            {% else %}
                باقی‌مانده‌ی امروز: {{ remaining }} از {{ limit }} تصویر
            {% endif %}
        </div>
        {% if remaining == 0 and not admin %}
            <div class="error">⚠️ سقف روزانه‌ی «مدل تصور» تموم شده. فردا دوباره امتحان کن.</div>
        {% else %}
        <form class="main-form" method="POST" action="/image">
            <input type="text" name="prompt" placeholder="مثلاً: یک گربه فضانورد روی ماه" value="{{ prompt or '' }}" autofocus required>
            <button type="submit">ساخت تصویر</button>
        </form>
        {% endif %}

        {% if prompt and image_url %}
            <div class="question">🖼️ {{ prompt }}</div>
            <div class="image-result">
                <p style="color:#999; font-size:13px;">⏳ ساخت تصویر ممکن است تا ۲۰ ثانیه طول بکشد...</p>
                <img src="{{ image_url }}" alt="{{ prompt }}"
                     onerror="this.onerror=null; this.style.display='none'; document.getElementById('img-error').style.display='block';">
                <div id="img-error" class="error" style="display:none;">
                    ⚠️ تصویر بارگذاری نشد. چند ثانیه صبر کن و دوباره امتحان کن.
                </div>
            </div>
        {% endif %}
        {% endif %}
        {% endif %}
    </div>

    <footer>ساخته شده توسط تیم فنی persian_ai</footer>
</body>
</html>
"""


def _server_busy() -> bool:
    return count_online() > ONLINE_LIMIT and not is_admin()


@app.route("/", methods=["GET"])
def welcome_or_chat():
    if "user_name" not in session:
        return render_template_string(WELCOME_TEMPLATE, site_name=SITE_NAME)
    return render_chat()


@app.route("/start", methods=["POST"])
def start():
    session.permanent = True
    name = request.form.get("user_name", "").strip()
    if name:
        # رمز مخصوص سازنده: اگه دقیقاً همین رو به‌جای اسم بزنه، پنل مدیریت باز می‌شه
        if ADMIN_SECRET and name == ADMIN_SECRET:
            session["is_admin"] = True
            session["user_name"] = "سازنده"
        else:
            session["user_name"] = name
    return redirect(url_for("welcome_or_chat"))


def render_chat(question=None, answer=None, error=None):
    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="chat",
        question=question,
        answer=answer,
        error=error,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        monthly_count=count_monthly(),
        online_count=count_online(),
        busy=_server_busy(),
    )


@app.route("/", methods=["POST"])
def index_post():
    if "user_name" not in session:
        return redirect(url_for("welcome_or_chat"))
    if _server_busy():
        return render_chat()

    question = request.form.get("question", "").strip()
    answer = None
    error = None
    if question:
        track_activity()  # فقط الان که واقعاً پیام فرستاده، به‌عنوان کاربر فعال ثبت می‌شود
        try:
            answer = answer_question(question, session.get("user_name"))
        except Exception as e:
            error = str(e)
    return render_chat(question=question, answer=answer, error=error)


@app.route("/image", methods=["GET", "POST"])
def image_page():
    if "user_name" not in session:
        return redirect(url_for("welcome_or_chat"))

    prompt = None
    image_url = None
    busy = _server_busy()

    if request.method == "POST" and not busy:
        prompt = request.form.get("prompt", "").strip()
        if prompt and check_daily_limit("free_image", DAILY_LIMIT_FREE_IMAGE):
            track_activity()  # فقط الان که واقعاً از ابزار استفاده کرده، ثبت می‌شود
            encoded_prompt = quote(prompt)
            image_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width=768&height=768&nologo=true&seed=42"
            )
            increment_daily_usage("free_image")
        elif prompt:
            prompt = None  # سقف تموم شده، پرامپت رو نشون نده

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="image",
        prompt=prompt,
        image_url=image_url,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        monthly_count=count_monthly(),
        online_count=count_online(),
        busy=busy,
        limit=DAILY_LIMIT_FREE_IMAGE,
        remaining=remaining_daily("free_image", DAILY_LIMIT_FREE_IMAGE),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"🌐 {SITE_NAME} در حال اجراست...")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=port)
