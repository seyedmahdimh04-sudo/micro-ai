"""
وب‌سایت هوش مصنوعی «میکرو» - نسخه پیشرفته با چت زنده (AJAX)، لوگو، بازخورد و پنل مدیریت
اجرا: python app.py
"""

import os
import secrets
from datetime import timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
from main import (
    answer_question, get_daily_micro_greeting, get_or_create_user,
    get_user_coins, deduct_user_coins, claim_channel_bonus,
    get_total_users, save_feedback, get_all_feedback
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"
LOGO_URL = "https://uploadkon.ir/uploads/805818_26ChatGPT-Image-Aug-18-2026-01-02-18-PM.png"
CHANNEL_LINK = "https://ble.ir/micro_ai"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")
COST_PER_MESSAGE = 1
CHANNEL_BONUS_COINS = 25
CHANNEL_DWELL_SECONDS = 15


# ---------------------------------------------------------------------------
# صفحه‌ی خوش‌آمد (پرسیدن اسم)
# ---------------------------------------------------------------------------
WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="{{ logo }}">
    <title>{{ site_name }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Tahoma, 'Segoe UI', sans-serif; }
        body {
            background: radial-gradient(circle at top, #161b22, #090c10);
            color: #f0f6fc; min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .box { text-align: center; padding: 40px; max-width: 420px; }
        .box img { width: 78px; height: 78px; border-radius: 20px; margin-bottom: 16px; box-shadow: 0 0 30px rgba(34,197,94,0.35); }
        .box h1 { font-size: 22px; margin-bottom: 6px; }
        .box p.sub { color: #8b949e; margin-bottom: 26px; font-size: 15px; }
        input[type=text] {
            width: 100%; padding: 14px 18px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.15);
            background: #161b22; color: #eee; font-size: 16px; margin-bottom: 14px; text-align: center;
        }
        button {
            width: 100%; padding: 14px; border-radius: 12px; border: none;
            background: #22c55e; color: #06210f; font-weight: bold; font-size: 16px; cursor: pointer;
        }
        button:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="box">
        <img src="{{ logo }}" alt="میکرو">
        <h1>سلام 👋<br>من میکرو هستم، چت‌بات persian_ai!</h1>
        <p class="sub">اسم شما؟</p>
        <form method="POST" action="/start">
            <input type="text" name="user_name" placeholder="اسم شما؟" autofocus required>
            <button type="submit">شروع گفتگو</button>
        </form>
    </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# قالب اصلی چت (AJAX + جلوه‌ی فکر کردن + تایپ زنده)
# ---------------------------------------------------------------------------
PAGE_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="{{ logo }}">
    <title>{{ site_name }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Tahoma, 'Segoe UI', sans-serif; }
        :root {
            --bg1: #090c10; --bg2: #0d1117; --card: #161b22; --border: rgba(255,255,255,0.1);
            --accent: #22c55e; --text: #f0f6fc; --muted: #8b949e;
        }
        body {
            background: radial-gradient(circle at top, var(--bg2), var(--bg1));
            color: var(--text); min-height: 100vh; display: flex; flex-direction: column;
        }
        .header-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 20px; border-bottom: 1px solid var(--border);
        }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand img {
            width: 34px; height: 34px; border-radius: 9px; transition: transform 0.35s ease;
        }
        .brand img.thinking { animation: pulseLogo 0.9s ease-in-out infinite; }
        @keyframes pulseLogo {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.35); }
        }
        .brand span { font-weight: 800; font-size: 15px; }
        .user-balance {
            background: rgba(34,197,94,0.15); border: 1px solid var(--accent);
            color: var(--accent); padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 700;
        }
        .header-right { display: flex; align-items: center; gap: 10px; }
        .admin-link { color: var(--muted); font-size: 12px; text-decoration: none; }

        .join-channel-bar {
            display: flex; justify-content: center; padding: 8px;
        }
        .join-channel-btn {
            background: linear-gradient(135deg, #0ea5e9, #2563eb);
            color: #fff; text-decoration: none; padding: 7px 16px; border-radius: 999px;
            font-size: 12px; font-weight: 700;
        }

        .main-container { max-width: 780px; width: 100%; margin: 0 auto; padding: 16px 20px; flex: 1; display: flex; flex-direction: column; }
        .chat-feed { flex: 1; display: flex; flex-direction: column; gap: 14px; margin-bottom: 15px; overflow-y: auto; }
        .chat-row { display: flex; gap: 10px; }
        .chat-row.user { justify-content: flex-end; }
        .chat-bubble { max-width: 82%; padding: 12px 18px; border-radius: 16px; font-size: 14px; line-height: 1.85; white-space: pre-wrap; }
        .chat-row.user .chat-bubble { background: #2563eb; color: #fff; border-bottom-left-radius: 4px; }
        .chat-row.assistant .chat-bubble { background: var(--card); border: 1px solid var(--border); border-bottom-right-radius: 4px; }

        .assistant-wrap { display: flex; flex-direction: column; gap: 6px; max-width: 82%; }
        .msg-actions { display: flex; gap: 8px; padding-right: 4px; }
        .msg-actions button {
            background: transparent; border: none; color: var(--muted); cursor: pointer; font-size: 13px;
        }
        .msg-actions button.active-like { color: #22c55e; }
        .msg-actions button.active-dislike { color: #ef4444; }

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
            border-radius: 50%; color: #000; font-size: 18px; cursor: pointer;
        }
        .send-btn:disabled { opacity: 0.5; }

        .error-msg { background: #3a1420; border: 1px solid #ef4444; color: #ffb3c0; padding: 12px 16px; border-radius: 12px; font-size: 13px; text-align: center; }

        footer { text-align: center; padding: 12px 20px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--border); }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="brand">
            <img src="{{ logo }}" id="brandLogo" alt="میکرو">
            <span>میکرو</span>
        </div>
        <div class="header-right">
            {% if admin %}<a class="admin-link" href="/admin">📊 پنل مدیریت</a>{% endif %}
            <div class="user-balance">🪙 <span id="coinBadge">{{ coins }}</span> سکه</div>
        </div>
    </div>

    <div class="join-channel-bar">
        <a href="{{ channel_link }}" target="_blank" id="channelLink" class="join-channel-btn">📢 عضویت در کانال میکرو (+۲۵ سکه)</a>
    </div>

    <div class="main-container">
        <div class="chat-feed" id="chatFeed"></div>
        <div id="errorBox"></div>
        <form id="chatForm" onsubmit="return false;">
            <div class="input-bar">
                <input type="text" id="chatInput" placeholder="اینجا با من گپ بزن..." autofocus>
                <button type="submit" class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
            </div>
        </form>
    </div>

    <footer>ساخته شده توسط تیم فنی persian_ai</footer>

    <script>
        const feed = document.getElementById('chatFeed');
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const logo = document.getElementById('brandLogo');
        const coinBadge = document.getElementById('coinBadge');
        const errorBox = document.getElementById('errorBox');
        let msgCounter = 0;
        let claimed = false;

        function addUserBubble(text) {
            const row = document.createElement('div');
            row.className = 'chat-row user';
            row.innerHTML = '<div class="chat-bubble"></div>';
            row.querySelector('.chat-bubble').innerText = text;
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
        }

        function addAssistantBubble(id) {
            const row = document.createElement('div');
            row.className = 'chat-row assistant';
            row.innerHTML = `
                <div class="assistant-wrap">
                    <div class="chat-bubble" id="bubble-${id}"></div>
                    <div class="msg-actions" id="actions-${id}" style="display:none;">
                        <button onclick="giveFeedback(${id}, 'like')" id="like-${id}">👍</button>
                        <button onclick="giveFeedback(${id}, 'dislike')" id="dislike-${id}">👎</button>
                        <button onclick="copyMsg(${id})">📋 کپی</button>
                    </div>
                </div>`;
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
        }

        function typeWriter(id, fullText, done) {
            const el = document.getElementById('bubble-' + id);
            let i = 0;
            const speed = 12;
            function step() {
                if (i <= fullText.length) {
                    el.innerText = fullText.slice(0, i);
                    feed.scrollTop = feed.scrollHeight;
                    i += 3;
                    setTimeout(step, speed);
                } else {
                    el.innerText = fullText;
                    if (done) done();
                }
            }
            step();
        }

        window.storeAnswers = {};

        function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            sendBtn.disabled = true;
            errorBox.innerHTML = '';
            addUserBubble(text);

            const id = ++msgCounter;
            addAssistantBubble(id);
            logo.classList.add('thinking');

            fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            })
            .then(function (res) {
                if (!res.ok) throw new Error('server');
                return res.json();
            })
            .then(function (data) {
                logo.classList.remove('thinking');
                if (data.error) {
                    document.getElementById('bubble-' + id).innerText = data.error;
                    sendBtn.disabled = false;
                    return;
                }
                window.storeAnswers[id] = data.answer;
                if (typeof data.coins === 'number') coinBadge.innerText = data.coins;
                typeWriter(id, data.answer, function () {
                    document.getElementById('actions-' + id).style.display = 'flex';
                    sendBtn.disabled = false;
                });
            })
            .catch(function () {
                logo.classList.remove('thinking');
                document.getElementById('bubble-' + id).innerText = '';
                errorBox.innerHTML = '<div class="error-msg">مشکلی در ارتباط با سرور پیش آمد! لطفا اینترنت خود را بررسی کنید.</div>';
                sendBtn.disabled = false;
            });
        }

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') sendMessage();
        });

        function copyMsg(id) {
            const text = window.storeAnswers[id] || '';
            navigator.clipboard.writeText(text);
        }

        function giveFeedback(id, verdict) {
            const q = document.querySelectorAll('.chat-row.user .chat-bubble');
            fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answer: window.storeAnswers[id] || '', verdict: verdict })
            });
            document.getElementById('like-' + id).classList.remove('active-like');
            document.getElementById('dislike-' + id).classList.remove('active-dislike');
            document.getElementById(verdict + '-' + id).classList.add('active-' + verdict);
        }

        // --- تشخیص عضویت در کانال با تایمر حضور (Visibility API) ---
        let hiddenAt = null;
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                hiddenAt = Date.now();
            } else if (hiddenAt && !claimed) {
                const elapsed = (Date.now() - hiddenAt) / 1000;
                if (elapsed >= {{ dwell_seconds }}) {
                    claimed = true;
                    fetch('/api/claim-channel', { method: 'POST' })
                        .then(function (r) { return r.json(); })
                        .then(function (data) {
                            if (data.granted && typeof data.coins === 'number') {
                                coinBadge.innerText = data.coins;
                            }
                        });
                }
                hiddenAt = null;
            }
        });
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="{{ logo }}">
    <title>پنل مدیریت میکرو</title>
    <style>
        * { box-sizing: border-box; font-family: Tahoma, sans-serif; }
        body { background: #0d1117; color: #f0f6fc; margin: 0; padding: 30px; }
        h1 { color: #22c55e; }
        .stat { background: #161b22; padding: 16px 22px; border-radius: 14px; display: inline-block; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        th, td { text-align: right; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 13px; vertical-align: top; }
        th { color: #8b949e; }
        .like { color: #22c55e; }
        .dislike { color: #ef4444; }
        a { color: #58a6ff; }
    </style>
</head>
<body>
    <a href="/">⬅ بازگشت به چت</a>
    <h1>📊 پنل مدیریت میکرو</h1>
    <div class="stat">👥 مجموع کاربران ثبت‌شده: <b>{{ total_users }}</b></div>
    <h3>بازخوردهای اخیر</h3>
    <table>
        <tr><th>کاربر</th><th>جواب میکرو</th><th>بازخورد</th><th>زمان</th></tr>
        {% for f in feedback %}
        <tr>
            <td>{{ f.username }}</td>
            <td>{{ f.answer[:150] }}</td>
            <td class="{{ f.verdict }}">{{ '👍 لایک' if f.verdict == 'like' else '👎 دیس‌لایک' }}</td>
            <td>{{ f.created_at }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


def get_user_id():
    if "uid" not in session:
        session["uid"] = secrets.token_hex(6)
    session.permanent = True
    return session["uid"]


def is_admin() -> bool:
    return session.get("is_admin", False)


@app.route("/", methods=["GET"])
def index():
    if "user_name" not in session:
        return render_template_string(WELCOME_TEMPLATE, site_name=SITE_NAME, logo=LOGO_URL)

    user_id = get_user_id()
    get_or_create_user(user_id, session.get("user_name", "کاربر"))

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        logo=LOGO_URL,
        coins=get_user_coins(user_id),
        admin=is_admin(),
        channel_link=CHANNEL_LINK,
        dwell_seconds=CHANNEL_DWELL_SECONDS,
    )


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
    return redirect(url_for("index"))


@app.route("/api/ask", methods=["POST"])
def api_ask():
    if "user_name" not in session:
        return jsonify({"error": "لطفاً اول اسمت رو وارد کن."}), 400

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "پیام خالیه!"}), 400

    user_id = get_user_id()
    user_name = session.get("user_name", "کاربر")
    coins = get_user_coins(user_id)

    if not is_admin() and coins < COST_PER_MESSAGE:
        return jsonify({
            "error": f"⚠️ سکه شما کافی نیست! برای افزایش موجودی از دکمه‌ی «افزایش اعتبار» تو ربات بله استفاده کن.",
        })

    history = session.get("history", [])
    answer, success = answer_question(question, user_name, history)

    if success and not is_admin():
        deduct_user_coins(user_id, COST_PER_MESSAGE)

    history.append({"q": question, "a": answer})
    session["history"] = history[-10:]
    session["last_answer"] = answer

    return jsonify({"answer": answer, "coins": get_user_coins(user_id)})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    if "user_name" not in session:
        return jsonify({"ok": False}), 400
    data = request.get_json(silent=True) or {}
    verdict = data.get("verdict")
    answer = data.get("answer", "")
    if verdict not in ("like", "dislike"):
        return jsonify({"ok": False}), 400
    save_feedback(get_user_id(), session.get("user_name", "کاربر"), "", answer, verdict)
    return jsonify({"ok": True})


@app.route("/api/claim-channel", methods=["POST"])
def api_claim_channel():
    if "user_name" not in session:
        return jsonify({"granted": False}), 400
    user_id = get_user_id()
    granted = claim_channel_bonus(user_id)
    return jsonify({"granted": granted, "coins": get_user_coins(user_id)})


@app.route("/admin", methods=["GET"])
def admin_panel():
    if not is_admin():
        return redirect(url_for("index"))
    return render_template_string(
        ADMIN_TEMPLATE,
        logo=LOGO_URL,
        total_users=get_total_users(),
        feedback=get_all_feedback(),
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
