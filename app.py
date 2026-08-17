"""
وب‌سایت هوش مصنوعی «میکرو»
اجرا: python app.py
"""

import os
import secrets
import json
from datetime import timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify, Response
from main import (
    get_daily_micro_greeting, get_or_create_user, get_user_coins, 
    deduct_user_coins, claim_channel_bonus, set_user_name, 
    answer_question_stream, save_feedback, get_admin_stats
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"

# همون قالب خودت + استایل‌های دکمه لایک و مودال
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
        .join-channel-btn {
            background: linear-gradient(135deg, #0ea5e9, #2563eb);
            color: #fff; text-decoration: none; padding: 7px 16px; border-radius: 999px;
            font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px;
            box-shadow: 0 4px 12px rgba(14,165,233,0.3); transition: 0.2s;
        }
        .join-channel-btn:hover { opacity: 0.9; transform: scale(1.03); }
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

        .cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .feature-card {
            background: var(--card); border: 1px solid var(--border);
            padding: 16px; border-radius: 16px; cursor: pointer;
            display: flex; align-items: center; justify-content: space-between; transition: 0.2s;
        }
        .feature-card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card-text { font-size: 14px; font-weight: 600; }
        
        .chat-feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; margin-bottom: 15px; }
        .chat-row { display: flex; gap: 10px; flex-direction: column; }
        .chat-row.user { align-items: flex-end; }
        .chat-row.assistant { align-items: flex-start; }
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

        /* --- قابلیت‌های جدید میکرو اضافه شده در اینجا --- */
        
        /* دایره چرخان خفن (نشانگر فکر کردن) */
        .spinner {
            width: 22px; height: 22px; border: 3px solid rgba(34, 197, 94, 0.2);
            border-top-color: var(--accent); border-radius: 50%;
            animation: spin 1s linear infinite; display: inline-block;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }

        /* دکمه‌های بازخورد */
        .action-btns { display: flex; gap: 10px; margin-top: 6px; padding: 0 5px; }
        .action-btns button { 
            background: transparent; border: none; color: var(--muted); cursor: pointer; 
            font-size: 13px; display: flex; align-items: center; gap: 4px; transition: 0.2s;
        }
        .action-btns button:hover { color: var(--text); transform: scale(1.1); }
        .action-btns button.like:hover { color: var(--accent); }
        .action-btns button.dislike:hover { color: #ef4444; }

        /* پاپ‌آپ گرفتن اسم اول کار */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); backdrop-filter: blur(5px);
            display: flex; align-items: center; justify-content: center; z-index: 1000;
        }
        .modal-box {
            background: var(--card); padding: 25px; border-radius: 15px; 
            border: 1px solid var(--border); text-align: center; width: 90%; max-width: 350px;
        }
        .modal-box p { font-size: 16px; margin-bottom: 15px; white-space: pre-line; line-height: 1.8; }
        .modal-box input {
            width: 100%; padding: 12px; border-radius: 10px; border: 1px solid var(--border);
            background: var(--bg1); color: var(--text); text-align: center; font-size: 15px; outline: none; margin-bottom: 15px;
        }
        .modal-box button {
            background: var(--accent); color: #000; border: none; padding: 10px 20px;
            border-radius: 10px; font-weight: bold; cursor: pointer; width: 100%;
        }
    </style>
</head>
<body class="theme-dark" id="pageBody">

    <!-- Onboarding Modal -->
    {% if show_onboarding %}
    <div class="modal-overlay" id="onboardingModal">
        <div class="modal-box">
            <p style="font-weight: bold; font-size: 18px;">سلام👋<br>من میکرو هستم، چت بات persian_ai!</p>
            <div style="font-family: monospace; color: var(--accent); margin-bottom: 10px;">
                --------------------------<br>
                |           اسم شما؟        |<br>
                ------------------------
            </div>
            <input type="text" id="nameInput" placeholder="اینجا اسمت رو بنویس...">
            <button onclick="saveName()">ثبت</button>
        </div>
    </div>
    {% endif %}

    <div class="header-bar">
        <div style="display: flex; gap: 10px;">
            <a href="/join_channel" target="_blank" class="join-channel-btn">
                📢 عضویت در کانال میکرو {% if bonus_available %}(+۳۰ سکه هدیه){% endif %}
            </a>
            {% if is_admin %}
            <a href="/admin" class="join-channel-btn" style="background: #ef4444; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);">
                👑 پنل مدیریت
            </a>
            {% endif %}
        </div>

        <div style="display:flex; align-items:center; gap:10px;">
            <div class="user-balance" id="coinDisplay">🪙 {{ coins }} سکه</div>
            <a href="https://ble.ir/micro_ai_bot" target="_blank" style="background:#eab308; color:#000; text-decoration:none; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700;">خرید سکه</a>
            <div class="theme-buttons">
                <button class="theme-btn" onclick="setTheme('dark')">🌙</button>
                <button class="theme-btn" onclick="setTheme('light')">☀️</button>
                <button class="theme-btn" onclick="setTheme('colorful')">🎨</button>
            </div>
        </div>
    </div>

    <div class="main-container">
        <div class="hero-banner">
            <div class="hero-rocket">🚀</div>
            <h1 class="hero-title">{{ greeting }}</h1>
        </div>

        {% if not history %}
        <div class="cards-grid" id="cardsGrid">
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
                <div class="chat-row user"><div class="chat-bubble">{{ item.q }}</div></div>
                <div class="chat-row assistant"><div class="chat-bubble">{{ item.a | replace('\n', '<br>') | safe }}</div></div>
            {% endfor %}
        </div>

        <!-- فرم استریم شد -->
        <form onsubmit="event.preventDefault(); sendStreamPrompt();" id="chatForm">
            <div class="input-bar">
                <input type="text" id="chatInput" placeholder="اینجا با من گپ بزن..." autocomplete="off" autofocus required>
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
        (function() { var t = localStorage.getItem('micro_theme'); if (t) setTheme(t); })();

        function sendPrompt(text) {
            document.getElementById('chatInput').value = text;
            sendStreamPrompt();
        }

        async function saveName() {
            const name = document.getElementById('nameInput').value.trim();
            if (!name) return;
            await fetch('/set_name', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            });
            document.getElementById('onboardingModal').style.display = 'none';
        }

        function createBubble(text, sender, id="") {
            const row = document.createElement('div');
            row.className = `chat-row ${sender}`;
            row.id = id;
            row.innerHTML = `<div class="chat-bubble">${text}</div>`;
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
            return row;
        }

        async function sendStreamPrompt() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;
            
            input.value = '';
            const grid = document.getElementById('cardsGrid');
            if(grid) grid.style.display = 'none'; // مخفی کردن کارت‌ها بعد از پیام اول

            createBubble(text, 'user');
            
            // نمایش دایره چرخان فکر کردن
            const botRowId = 'bot-' + Date.now();
            const botRow = createBubble('<div class="spinner"></div>', 'assistant', botRowId);
            const botBubble = botRow.querySelector('.chat-bubble');

            let currentAnswer = "";

            try {
                const response = await fetch('/chat_stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: text})
                });

                if (response.status === 402) throw new Error("سکه کافی نیست");
                if (!response.ok) throw new Error("NetworkError");

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let isFirstChunk = true;

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, {stream: true});
                    currentAnswer += chunk;
                    
                    if (isFirstChunk) {
                        botBubble.innerHTML = ""; // حذف دایره و شروع تایپ
                        isFirstChunk = false;
                    }
                    botBubble.innerHTML = currentAnswer.replace(/\\n/g, '<br>');
                    feed.scrollTop = feed.scrollHeight;
                }

                // اضافه کردن دکمه‌های بازخورد
                const btns = document.createElement('div');
                btns.className = "action-btns";
                btns.innerHTML = `
                    <button class="like" onclick="sendFeedback(this, '${encodeURIComponent(text)}', '${encodeURIComponent(currentAnswer)}', 'like')">👍</button>
                    <button class="dislike" onclick="sendFeedback(this, '${encodeURIComponent(text)}', '${encodeURIComponent(currentAnswer)}', 'dislike')">👎</button>
                    <button onclick="copyText('${encodeURIComponent(currentAnswer)}')">📋 کپی</button>
                `;
                botRow.appendChild(btns);

                // آپدیت موجودی سکه در صفحه
                const coinRes = await fetch('/get_coins');
                const coinData = await coinRes.json();
                document.getElementById('coinDisplay').innerText = `🪙 ${coinData.coins} سکه`;

            } catch (err) {
                if(err.message === "NetworkError" || err.name === "TypeError") {
                    botBubble.innerHTML = "مشکلی در ارتباط با سرور پیش آمد!<br>لطفا اینترنت خود را بررسی کنید!";
                } else if(err.message === "سکه کافی نیست") {
                    botBubble.innerHTML = "⚠️ سکه شما برای گفتگو کافی نیست! برای افزایش موجودی به ربات بله مراجعه کنید.";
                } else {
                    botBubble.innerHTML = err.message;
                }
            }
        }

        async function sendFeedback(btn, q, a, type) {
            btn.parentElement.innerHTML = `<span style="font-size:11px; color:var(--accent);">ثبت شد ✔️</span>`;
            await fetch('/feedback', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ question: decodeURIComponent(q), answer: decodeURIComponent(a), type: type })
            });
        }

        function copyText(encodedText) {
            navigator.clipboard.writeText(decodeURIComponent(encodedText));
            alert("کپی شد!");
        }
    </script>
</body>
</html>
"""

# قالب پنل ادمین
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8"><title>پنل مدیریت میکرو</title>
    <style>
        body { font-family: Tahoma; background: #090c10; color: #fff; padding: 20px; }
        .card { background: #161b22; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #30363d; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #30363d; padding: 10px; text-align: right; }
        th { background: #21262d; }
        .like { color: #22c55e; font-weight: bold; }
        .dislike { color: #ef4444; font-weight: bold; }
        a { color: #58a6ff; text-decoration: none; display: inline-block; margin-bottom: 15px; }
    </style>
</head>
<body>
    <a href="/">🔙 بازگشت به میکرو</a>
    <h1>👑 پنل اختصاصی مدیریت PERSIAN_AI</h1>
    <div class="card">
        <h3>📊 آمار کلی</h3>
        <p>تعداد کل کاربران ثبت‌نامی: <b style="color:#22c55e; font-size:20px;">{{ stats.total_users }}</b> نفر</p>
    </div>
    <div class="card">
        <h3>💬 بازخوردهای اخیر کاربران</h3>
        <table>
            <tr><th>کاربر UID</th><th>سوال کاربر</th><th>بازخورد</th></tr>
            {% for f in stats.feedbacks %}
            <tr>
                <td style="font-size:12px; color:#8b949e;">{{ f.uid }}</td>
                <td>{{ f.q }}</td>
                <td class="{{ f.type }}">{% if f.type == 'like' %}لایک 👍{% else %}دیس‌لایک 👎{% endif %}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    user_id = request.args.get("uid") or session.get("uid", secrets.token_hex(6))
    session["uid"] = user_id
    user_data = get_or_create_user(user_id)
    
    # اگر کاربر اسمش "کاربر" باشه (یعنی تازه اومده) مدال براش باز میشه
    show_onboarding = (user_data["username"] == "کاربر")
    is_admin = (user_id == "admin_persian_ai")

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        greeting=get_daily_micro_greeting(user_data["username"] if not show_onboarding else ""),
        coins=user_data["coins"],
        bonus_available=not user_data["has_channel_bonus"],
        history=session.get("history", []),
        show_onboarding=show_onboarding,
        is_admin=is_admin
    )

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    user_id = session.get("uid")
    data = request.json
    question = data.get("question", "")
    
    user_data = get_or_create_user(user_id)
    
    # ادمین سکه نامحدود داره
    if user_id != "admin_persian_ai" and user_data["coins"] < 5:
        return Response("سکه کافی نیست", status=402)

    def generate():
        history = session.get("history", [])
        success = False
        
        for chunk in answer_question_stream(question, user_data["username"], history):
            success = True 
            yield chunk

        if success:
            deduct_user_coins(user_id, 5)

    return Response(generate(), mimetype="text/plain")

@app.route("/set_name", methods=["POST"])
def set_name_route():
    user_id = session.get("uid")
    name = request.json.get("name")
    if user_id and name:
        set_user_name(user_id, name)
    return jsonify({"status": "ok"})

@app.route("/feedback", methods=["POST"])
def feedback():
    user_id = session.get("uid")
    data = request.json
    save_feedback(user_id, data.get("question"), data.get("answer"), data.get("type"))
    return jsonify({"status": "saved"})

@app.route("/get_coins", methods=["GET"])
def get_coins_route():
    user_id = session.get("uid")
    return jsonify({"coins": get_user_coins(user_id)})

@app.route("/admin")
def admin_dashboard():
    user_id = session.get("uid")
    if user_id != "admin_persian_ai":
        return "⚠️ شما دسترسی به این بخش ندارید!", 403
    stats = get_admin_stats()
    return render_template_string(ADMIN_TEMPLATE, stats=stats)

@app.route("/join_channel")
def join_channel():
    uid = session.get("uid")
    if uid:
        claim_channel_bonus(uid)
    return redirect("https://ble.ir/persian_ai")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))