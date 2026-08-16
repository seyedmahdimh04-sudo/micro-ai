"""
وب‌سایت و مینی‌اپ هوش مصنوعی «میکرو»
اجرا: python app.py
"""

import os
import secrets
from datetime import timedelta
from urllib.parse import quote
from flask import Flask, request, render_template_string, session, redirect, url_for
from main import (
    answer_question, get_daily_micro_greeting, get_or_create_user,
    get_user_coins, deduct_user_coins, claim_channel_bonus
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_name }}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Vazirmatn, Tahoma, sans-serif; }
        :root {
            --bg1: #090c10; --bg2: #0d1117; --card: #161b22; --border: rgba(255,255,255,0.1);
            --accent: #22c55e; --text: #f0f6fc; --muted: #8b949e; --btn-bg: #21262d;
        }
        body.theme-light {
            --bg1: #f6f8fa; --bg2: #ffffff; --card: #eaeef2; --border: rgba(0,0,0,0.1);
            --accent: #16a34a; --text: #1f2328; --muted: #656d76; --btn-bg: #d0d7de;
        }
        body.theme-colorful {
            --bg1: #1a0b2e; --bg2: #261245; --card: #3b1b6d; --border: rgba(255,255,255,0.15);
            --accent: #ec4899; --text: #ffffff; --muted: #d8b4fe; --btn-bg: #4c1d95;
        }
        body {
            background: radial-gradient(circle at top, var(--bg2), var(--bg1));
            color: var(--text); min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between;
        }
        .header-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 20px; border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2); backdrop-filter: blur(10px);
        }
        .mode-tags { display: flex; gap: 8px; flex-wrap: wrap; }
        .tag-pill {
            background: var(--btn-bg); border: 1px solid var(--border);
            padding: 6px 14px; border-radius: 999px; font-size: 12px;
            color: var(--text); display: flex; align-items: center; gap: 6px; cursor: pointer;
        }
        .tag-pill.active { border-color: var(--accent); color: var(--accent); }
        .user-balance {
            background: rgba(34,197,94,0.15); border: 1px solid var(--accent);
            color: var(--accent); padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 700;
        }
        .theme-buttons { display: flex; gap: 6px; }
        .theme-btn {
            background: var(--card); border: 1px solid var(--border);
            color: var(--text); padding: 4px 8px; border-radius: 8px; font-size: 11px; cursor: pointer;
        }
        
        .main-container { max-width: 820px; width: 100%; margin: 0 auto; padding: 20px; flex: 1; display: flex; flex-direction: column; }
        
        .hero-banner { text-align: center; margin: 15px 0 25px; }
        .hero-rocket { font-size: 44px; margin-bottom: 10px; animation: float 3s ease-in-out infinite; }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        .hero-title { font-size: 26px; font-weight: 800; color: var(--accent); margin-bottom: 6px; }
        
        .bonus-box {
            background: rgba(234, 179, 8, 0.1); border: 1px dashed #eab308;
            color: #facc15; padding: 10px 15px; border-radius: 12px; font-size: 13px; text-align: center; margin-bottom: 15px;
        }

        .cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .feature-card {
            background: var(--card); border: 1px solid var(--border);
            padding: 16px; border-radius: 16px; cursor: pointer;
            display: flex; align-items: center; justify-content: space-between; transition: 0.2s;
        }
        .feature-card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card-text { font-size: 14px; font-weight: 600; }
        
        .chat-feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; margin-bottom: 15px; }
        .chat-row { display: flex; gap: 10px; }
        .chat-row.user { justify-content: flex-end; }
        .chat-bubble {
            max-width: 80%; padding: 12px 18px; border-radius: 16px; font-size: 14px; line-height: 1.8;
        }
        .chat-row.user .chat-bubble { background: #2563eb; color: #fff; border-bottom-left-radius: 4px; }
        .chat-row.assistant .chat-bubble { background: var(--card); border: 1px solid var(--border); border-bottom-right-radius: 4px; }

        .input-bar {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 18px; display: flex; align-items: center; padding: 6px 12px; gap: 8px;
        }
        .input-bar input {
            flex: 1; background: transparent; border: none; outline: none;
            color: var(--text); font-size: 15px; padding: 10px 4px;
        }
        .send-btn {
            background: var(--accent); border: none; width: 40px; height: 40px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            color: #000; font-size: 18px; cursor: pointer; transition: 0.2s;
        }
        .send-btn:hover { transform: scale(1.05); }

        .footer-credits {
            text-align: center; padding: 15px 20px; font-size: 11px;
            color: var(--muted); border-top: 1px solid var(--border);
            display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px;
        }
        .footer-credits a { color: var(--muted); text-decoration: none; }
        .footer-credits a:hover { color: var(--accent); }
    </style>
</head>
<body class="theme-dark" id="pageBody">

    <div class="header-bar">
        <div class="mode-tags">
            <div class="tag-pill active">⚡ حالت استدلال عمیق</div>
            <div class="tag-pill">✨ خلاصه‌ساز کپسولی</div>
            <div class="tag-pill">🔤 مترجم سلیس</div>
            <div class="tag-pill">🪄 ویراستار ادبی</div>
        </div>

        <div style="display:flex; align-items:center; gap:10px;">
            <div class="user-balance">🪙 {{ coins }} سکه</div>
            <a href="https://ble.ir/micro_ai_bot" target="_blank" style="background:#eab308; color:#000; text-decoration:none; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700;">خرید سکه</a>
            <div class="theme-buttons">
                <button class="theme-btn" onclick="setTheme('dark')">🌙</button>
                <button class="theme-btn" onclick="setTheme('light')">☀️</button>
                <button class="theme-btn" onclick="setTheme('colorful')">🎨</button>
            </div>
        </div>
    </div>

    <div class="main-container">
        {% if bonus_available %}
        <div class="bonus-box">
            🎁 عضویت در کانال میکرو = ۴۰ سکه رایگان! <a href="/claim_bonus" style="color:#fff; font-weight:700; text-decoration:underline; margin-right:8px;">دریافت هدیه</a>
        </div>
        {% endif %}

        <div class="hero-banner">
            <div class="hero-rocket">🚀</div>
            <h1 class="hero-title">{{ greeting }}</h1>
        </div>

        {% if not history %}
        <div class="cards-grid">
            <div class="feature-card" onclick="sendPrompt('بمب انرژی و انگیزه روزانه برای پیشرفت')">
                <span class="card-text">بمب انرژی و انگیزه روزانه</span>
                <span>🔥</span>
            </div>
            <div class="feature-card" onclick="sendPrompt('چند دانستنی و گیم جذاب به من معرفی کن')">
                <span class="card-text">دنیای گیم و سرگرمی</span>
                <span>🎮</span>
            </div>
            <div class="feature-card" onclick="sendPrompt('ایده‌های ناب برنامه‌نویسی و هوش مصنوعی بده')">
                <span class="card-text">ایده‌های ناب برنامه‌نویسی</span>
                <span>🚀</span>
            </div>
            <div class="feature-card" onclick="sendPrompt('شگفتی‌ها و اسرار علمی نجوم و فضا را بگو')">
                <span class="card-text">اسرار علمی نجوم و فضا</span>
                <span>🌌</span>
            </div>
        </div>
        {% endif %}

        <div class="chat-feed" id="chatFeed">
            {% for item in history %}
                <div class="chat-row user">
                    <div class="chat-bubble">{{ item.q }}</div>
                </div>
                <div class="chat-row assistant">
                    <div class="chat-bubble">{{ item.a | replace('\n', '<br>') | safe }}</div>
                </div>
            {% endfor %}
        </div>

        <form method="POST" action="/" id="chatForm">
            <div class="input-bar">
                <input type="text" name="question" id="chatInput" placeholder="اینجا با من گپ بزن..." autofocus required>
                <button type="submit" class="send-btn">➤</button>
            </div>
        </form>
    </div>

    <div class="footer-credits">
        <span>جهت ارتباط با پشتیبان (بله): <a href="https://ble.ir/admin_persian_ai" target="_blank">@admin_persian_ai</a></span>
        <span>کانال توسعه‌دهنده (بله): <a href="https://ble.ir/persian_Ai" target="_blank">@persian_Ai</a></span>
    </div>

    <script>
        const feed = document.getElementById('chatFeed');
        if (feed) feed.scrollTop = feed.scrollHeight;

        function setTheme(t) {
            document.body.classList.remove('theme-dark', 'theme-light', 'theme-colorful');
            document.body.classList.add('theme-' + t);
            localStorage.setItem('micro_theme', t);
        }
        (function() {
            var t = localStorage.getItem('micro_theme');
            if (t) setTheme(t);
        })();

        function sendPrompt(text) {
            document.getElementById('chatInput').value = text;
            document.getElementById('chatForm').submit();
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    user_id = request.args.get("uid") or session.get("uid", secrets.token_hex(6))
    session["uid"] = user_id
    user_data = get_or_create_user(user_id)

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            # کسر ۵ سکه به ازای هر چت
            if deduct_user_coins(user_id, 5):
                history = session.get("history", [])
                answer = answer_question(question, "کاربر عزیز", history)
                history.append({"q": question, "a": answer})
                session["history"] = history[-10:]
            else:
                history = session.get("history", [])
                history.append({"q": question, "a": "⚠️ سکه شما تمام شده است! برای شارژ سکه به ربات بله مراجعه کنید: https://ble.ir/micro_ai_bot"})
                session["history"] = history
            return redirect(url_for("index", uid=user_id))

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        greeting=get_daily_micro_greeting("عزیز"),
        coins=get_user_coins(user_id),
        bonus_available=not user_data["has_channel_bonus"],
        history=session.get("history", [])
    )

@app.route("/claim_bonus")
def claim_bonus():
    uid = session.get("uid")
    if uid:
        claim_channel_bonus(uid)
    return redirect(url_for("index", uid=uid))

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))