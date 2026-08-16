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
from main import answer_question, get_random_fun, get_daily_headlines

app = Flask(__name__)
# کلید امن برای session (روی Render حتماً به‌عنوان متغیر محیطی SECRET_KEY تنظیمش کن)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
# مهم: session تا ۳۰ روز باقی می‌مونه، حتی اگه مرورگر بسته بشه
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"

# رمز مخصوص سازنده برای باز کردن پنل مدیریت و رفع محدودیت‌ها.
# پیشنهاد می‌شود این مقدار را روی Render به‌عنوان متغیر محیطی ADMIN_SECRET ست کنید.
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")

# محدودیت روزانه‌ی هر کاربر برای ابزار «مدل تصور» (تصویرساز رایگان)
DAILY_LIMIT_FREE_IMAGE = 5

# چند سؤال پیشنهادی برای شروع سریع گفتگو
QUICK_QUESTIONS = [
    "آخرین اخبار امروز چیه؟",
    "قیمت طلا و دلار امروز چنده؟",
    "یه جمله انگیزشی بگو",
    "هوای امروز تهران چطوره؟",
]

# ---------------------------------------------------------------------------
# آمار داخلی (فقط برای کنترل ازدحام سرور؛ دیگر رو صفحه نمایش داده نمی‌شود)
# ---------------------------------------------------------------------------
online_users = {}              # user_id -> آخرین زمان فعالیت
image_usage = defaultdict(lambda: {"date": None, "count": 0})  # user_id -> مصرف روزانه تصویر

ONLINE_WINDOW_SECONDS = 90
ONLINE_LIMIT = 30              # سقف بالاتری گذاشتیم چون دیگه نمایش داده نمی‌شه، فقط محافظتیه


def get_user_id():
    """شناسه‌ی یکتا برای هر کاربر (بر اساس session)"""
    session.permanent = True
    if "uid" not in session:
        session["uid"] = secrets.token_hex(8)
    return session["uid"]


def track_activity():
    uid = get_user_id()
    online_users[uid] = time.time()


def count_online():
    now = time.time()
    stale = [u for u, t in online_users.items() if now - t > ONLINE_WINDOW_SECONDS]
    for u in stale:
        del online_users[u]
    return len(online_users)


def is_admin() -> bool:
    return session.get("is_admin", False)


def check_daily_limit(tool_key: str, limit: int) -> bool:
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
        return -1
    uid = get_user_id()
    today_str = date.today().isoformat()
    usage = image_usage[f"{tool_key}:{uid}"]
    if usage["date"] != today_str:
        return limit
    return max(0, limit - usage["count"])


def update_streak():
    """استریک روزانه‌ی کاربر را به‌روزرسانی می‌کند و پیام مناسب برمی‌گرداند (یا None)"""
    today_str = date.today().isoformat()
    last_visit = session.get("last_visit")
    streak = session.get("streak", 0)

    if last_visit == today_str:
        return None  # امروز قبلاً ثبت شده، پیامی نده

    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    if last_visit == yesterday_str:
        streak += 1
    else:
        streak = 1

    session["last_visit"] = today_str
    session["streak"] = streak

    if streak >= 2:
        return f"🔥 {streak} روز پشت‌سرهم اومدی سراغ میکرو! همینطوری ادامه بده."
    return None


def get_history():
    return session.get("history", [])


def push_history(question: str, answer: str):
    history = session.get("history", [])
    history.append({"q": question, "a": answer})
    session["history"] = history[-6:]
    session.modified = True


# ---------------------------------------------------------------------------
# قالب صفحه‌ی خوش‌آمدگویی (قبل از ورود به چت)
# ---------------------------------------------------------------------------
WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="میکرو، دستیار هوش مصنوعی فارسی‌زبان رایگان: اخبار روز، گفتگوی هوشمند و ساخت تصویر با هوش مصنوعی.">
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
        .box { text-align: center; padding: 40px; max-width: 420px; }
        .box h1 { font-size: 26px; color: #7dd3fc; margin-bottom: 6px; }
        .box p { color: #999; margin-bottom: 26px; }
        input[type=text] {
            width: 100%; padding: 14px 18px; border-radius: 10px;
            border: 1px solid #444; background: #2a2a3d; color: #eee;
            font-size: 16px; margin-bottom: 14px; box-sizing: border-box; text-align: center;
        }
        button {
            width: 100%; padding: 14px; border-radius: 10px; border: none;
            background: #7dd3fc; color: #1e1e2f; font-weight: bold; font-size: 16px; cursor: pointer;
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
        :root {
            --bg1: #1e1e2f; --bg2: #2a2a4a; --text: #eee; --card: #2a2a3d;
            --accent: #7dd3fc; --accent-text: #1e1e2f; --muted: #999;
        }
        body.theme-light {
            --bg1: #f4f6fb; --bg2: #e7ecf7; --text: #1c1c28; --card: #ffffff;
            --accent: #4f8ef7; --accent-text: #ffffff; --muted: #666;
        }
        body.theme-colorful {
            --bg1: #2b1055; --bg2: #7597de; --text: #fff; --card: #3a1c71;
            --accent: #ffaf7b; --accent-text: #2b1055; --muted: #d9c9ff;
        }
        body {
            font-family: Tahoma, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, var(--bg1), var(--bg2));
            color: var(--text);
            margin: 0; padding: 0; min-height: 100vh;
        }
        .topbar {
            display: flex; justify-content: flex-end; gap: 8px;
            padding: 10px 20px; font-size: 12px;
        }
        .theme-btn {
            background: var(--card); border: none; color: var(--text);
            padding: 4px 10px; border-radius: 999px; cursor: pointer; font-size: 12px;
        }
        header { text-align: center; padding: 6px 20px 10px; }
        header h1 { font-size: 28px; color: var(--accent); margin: 0; }
        header p { color: var(--muted); font-size: 14px; margin-top: 8px; }
        .container { max-width: 750px; margin: 10px auto; padding: 0 20px 60px; }

        .streak-banner {
            background: var(--card); border-radius: 12px; padding: 10px 16px;
            margin-bottom: 16px; font-size: 14px; text-align: center;
        }

        .headlines { background: var(--card); border-radius: 14px; padding: 16px 20px; margin-bottom: 20px; }
        .headlines h3 { margin: 0 0 10px; font-size: 15px; color: var(--accent); }
        .headlines ul { margin: 0; padding-right: 18px; font-size: 14px; line-height: 1.9; }

        .quick-questions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
        .quick-questions button {
            background: var(--card); color: var(--text); border: 1px solid rgba(255,255,255,0.15);
            padding: 8px 14px; border-radius: 999px; font-size: 13px; cursor: pointer;
        }
        .quick-questions button:hover { border-color: var(--accent); }

        form.main-form { display: flex; gap: 10px; margin-bottom: 16px; }
        input[type=text] {
            flex: 1; padding: 14px 18px; border-radius: 10px; border: 1px solid #444;
            background: var(--card); color: var(--text); font-size: 16px;
        }
        button.submit-btn {
            padding: 14px 28px; border-radius: 10px; border: none;
            background: var(--accent); color: var(--accent-text); font-weight: bold;
            font-size: 16px; cursor: pointer;
        }
        button.submit-btn:hover { opacity: 0.9; }

        .question { color: #fbbf24; font-size: 18px; margin-bottom: 16px; }
        .answer-box { position: relative; }
        .answer {
            white-space: pre-wrap; background: var(--card); padding: 24px;
            border-radius: 14px; line-height: 1.9; font-size: 16px;
        }
        .copy-btn {
            position: absolute; top: 10px; left: 10px; background: rgba(255,255,255,0.1);
            border: none; color: var(--text); padding: 5px 10px; border-radius: 8px;
            font-size: 12px; cursor: pointer;
        }
        .error { background: #4a1e2a; color: #ffb3c0; padding: 16px; border-radius: 10px; }
        .limit-note { color: var(--muted); font-size: 13px; margin-bottom: 14px; }
        footer { text-align: center; color: var(--muted); font-size: 13px; margin-top: 40px; }
        .tabs { display: flex; gap: 10px; justify-content: center; margin-bottom: 24px; flex-wrap: wrap; }
        .tab { padding: 10px 24px; border-radius: 999px; text-decoration: none; color: var(--text); background: var(--card); font-size: 14px; }
        .tab.active { background: var(--accent); color: var(--accent-text); font-weight: bold; }
        .image-result { text-align: center; }
        .image-result img { max-width: 100%; border-radius: 14px; margin-top: 10px; }
        .admin-badge { background: #22c55e; color: #06210f; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: bold; margin-right: 6px; }
        .fun-btn {
            display: block; margin: 0 auto 20px; background: var(--card); color: var(--text);
            border: 1px dashed var(--accent); padding: 10px 18px; border-radius: 999px;
            font-size: 13px; cursor: pointer;
        }
    </style>
</head>
<body class="theme-dark" id="pageBody">
    <div class="topbar">
        <button class="theme-btn" onclick="setTheme('dark')">🌙 تیره</button>
        <button class="theme-btn" onclick="setTheme('light')">☀️ روشن</button>
        <button class="theme-btn" onclick="setTheme('colorful')">🎨 رنگی</button>
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

        {% if streak_message %}
            <div class="streak-banner">{{ streak_message }}</div>
        {% endif %}

        {% if mode == 'chat' %}

        {% if not question and headlines %}
        <div class="headlines">
            <h3>📰 چند خبر داغ امروز</h3>
            <ul>
                {% for h in headlines %}
                <li>{{ h.title }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if not question %}
        <div class="quick-questions">
            {% for q in quick_questions %}
            <button type="button" onclick="askQuick('{{ q|replace("'", "") }}')">{{ q }}</button>
            {% endfor %}
        </div>
        <button class="fun-btn" onclick="window.location.href='/fun'">🎲 حوصلم سر رفته، یه چیز جالب بگو</button>
        {% endif %}

        <form class="main-form" id="chatForm" method="POST" action="/">
            <input type="text" name="question" id="questionInput" placeholder="سؤال خودت رو بپرس..." value="{{ question or '' }}" autofocus required>
            <button class="submit-btn" type="submit">پرسیدن</button>
        </form>

        {% if question %}
            <div class="question">❓ {{ question }}</div>
            {% if error %}
                <div class="error">⚠️ خطا: {{ error }}</div>
            {% else %}
            <div class="answer-box">
                <button class="copy-btn" onclick="copyAnswer()">📋 کپی</button>
                <div class="answer" id="answerText">{{ answer }}</div>
            </div>
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
            <button class="submit-btn" type="submit">ساخت تصویر</button>
        </form>
        {% endif %}

        {% if prompt and image_url %}
            <div class="question">🖼️ {{ prompt }}</div>
            <div class="image-result">
                <p style="color:var(--muted); font-size:13px;">⏳ ساخت تصویر ممکن است تا ۲۰ ثانیه طول بکشد...</p>
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

    <script>
        function setTheme(name) {
            document.body.classList.remove('theme-dark', 'theme-light', 'theme-colorful');
            document.body.classList.add('theme-' + name);
            try { localStorage.setItem('microTheme', name); } catch (e) {}
        }
        (function () {
            try {
                var saved = localStorage.getItem('microTheme');
                if (saved) setTheme(saved);
            } catch (e) {}
        })();
        function askQuick(q) {
            document.getElementById('questionInput').value = q;
            document.getElementById('chatForm').submit();
        }
        function copyAnswer() {
            var text = document.getElementById('answerText').innerText;
            navigator.clipboard.writeText(text).then(function () {
                var btn = document.querySelector('.copy-btn');
                var old = btn.innerText;
                btn.innerText = '✅ کپی شد';
                setTimeout(function () { btn.innerText = old; }, 1500);
            });
        }
    </script>
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
        if ADMIN_SECRET and name == ADMIN_SECRET:
            session["is_admin"] = True
            session["user_name"] = "سازنده"
        else:
            session["user_name"] = name
    return redirect(url_for("welcome_or_chat"))


def render_chat(question=None, answer=None, error=None):
    headlines = get_daily_headlines() if not question else []
    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="chat",
        question=question,
        answer=answer,
        error=error,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        busy=_server_busy(),
        quick_questions=QUICK_QUESTIONS,
        headlines=headlines,
        streak_message=None,
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
    streak_message = None
    if question:
        track_activity()
        streak_message = update_streak()
        try:
            answer = answer_question(question, session.get("user_name"), get_history())
            push_history(question, answer)
        except Exception as e:
            error = str(e)

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="chat",
        question=question,
        answer=answer,
        error=error,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        busy=_server_busy(),
        quick_questions=QUICK_QUESTIONS,
        headlines=[],
        streak_message=streak_message,
    )


@app.route("/fun", methods=["GET"])
def fun():
    if "user_name" not in session:
        return redirect(url_for("welcome_or_chat"))
    track_activity()
    joke = get_random_fun()
    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="chat",
        question="🎲 یه چیز جالب بگو",
        answer=joke,
        error=None,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        busy=_server_busy(),
        quick_questions=QUICK_QUESTIONS,
        headlines=[],
        streak_message=None,
    )


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
            track_activity()
            encoded_prompt = quote(prompt)
            image_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width=768&height=768&nologo=true&seed=42"
            )
            increment_daily_usage("free_image")
        elif prompt:
            prompt = None

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="image",
        prompt=prompt,
        image_url=image_url,
        admin=is_admin(),
        user_name=session.get("user_name", ""),
        busy=busy,
        limit=DAILY_LIMIT_FREE_IMAGE,
        remaining=remaining_daily("free_image", DAILY_LIMIT_FREE_IMAGE),
        quick_questions=QUICK_QUESTIONS,
        headlines=[],
        streak_message=None,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"🌐 {SITE_NAME} در حال اجراست...")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=port)
