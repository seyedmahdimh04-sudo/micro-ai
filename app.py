import os
import secrets
from flask import Flask, request, render_template_string, session, redirect, url_for, Response, jsonify
from main import (
    get_or_create_user, get_user_coins, deduct_user_coins, 
    set_user_name, answer_question_stream, save_feedback, get_admin_stats
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))

SITE_NAME = "هوش مصنوعی رایکا"

# --- قالب اصلی سایت (شامل Onboarding، استریم و دکمه‌ها) ---
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
        :root { --bg1: #090c10; --bg2: #0d1117; --card: #161b22; --border: rgba(255,255,255,0.1); --accent: #22c55e; --text: #f0f6fc; --muted: #8b949e; }
        body { background: radial-gradient(circle at top, var(--bg2), var(--bg1)); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid var(--border); background: rgba(0,0,0,0.2); backdrop-filter: blur(10px); }
        .main-container { max-width: 820px; width: 100%; margin: 0 auto; padding: 20px; flex: 1; display: flex; flex-direction: column; position: relative; }
        
        /* Chat Area */
        .chat-feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; margin-bottom: 15px; padding-bottom: 20px; }
        .chat-row { display: flex; gap: 10px; width: 100%; }
        .chat-row.user { justify-content: flex-end; }
        .chat-bubble { max-width: 80%; padding: 14px 18px; border-radius: 16px; font-size: 15px; line-height: 1.8; position: relative; }
        .chat-row.user .chat-bubble { background: #2563eb; color: #fff; border-bottom-left-radius: 4px; }
        .chat-row.assistant .chat-bubble { background: var(--card); border: 1px solid var(--border); border-bottom-right-radius: 4px; }
        
        /* Thinking Spinner */
        .spinner {
            width: 24px; height: 24px; border: 3px solid rgba(34, 197, 94, 0.2);
            border-top-color: var(--accent); border-radius: 50%;
            animation: spin 1s linear infinite; display: inline-block;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }

        /* Action Buttons (Like, Dislike, Copy) */
        .action-btns { display: flex; gap: 8px; margin-top: 10px; border-top: 1px solid var(--border); padding-top: 8px; }
        .action-btns button { 
            background: transparent; border: none; color: var(--muted); cursor: pointer; 
            font-size: 14px; transition: 0.2s; display: flex; align-items: center; gap: 4px;
        }
        .action-btns button:hover { color: var(--accent); transform: scale(1.1); }
        .action-btns button.dislike:hover { color: #ef4444; }

        /* Input Area */
        .input-bar { background: var(--card); border: 1px solid var(--border); border-radius: 18px; display: flex; padding: 6px 12px; gap: 8px; }
        .input-bar input { flex: 1; background: transparent; border: none; outline: none; color: var(--text); font-size: 15px; }
        .send-btn { background: var(--accent); border: none; width: 40px; height: 40px; border-radius: 50%; color: #000; font-size: 18px; cursor: pointer; }

        /* Onboarding Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); backdrop-filter: blur(5px);
            display: flex; align-items: center; justify-content: center; z-index: 1000;
        }
        .modal-box {
            background: var(--card); padding: 30px; border-radius: 20px; border: 1px solid var(--border);
            text-align: center; width: 90%; max-width: 400px;
        }
        .modal-box h2 { color: var(--accent); margin-bottom: 15px; }
        .modal-box input {
            width: 100%; padding: 12px; border-radius: 10px; border: 1px solid var(--border);
            background: var(--bg1); color: var(--text); margin: 15px 0; text-align: center; font-size: 16px; outline: none;
        }
        .modal-box input:focus { border-color: var(--accent); }
        .modal-box button {
            background: var(--accent); color: #000; border: none; padding: 12px 30px;
            border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; width: 100%;
        }
    </style>
</head>
<body>

    <!-- Onboarding Modal -->
    {% if not username %}
    <div class="modal-overlay" id="onboardingModal">
        <div class="modal-box">
            <h2 style="font-size: 28px;">سلام 👋</h2>
            <p style="font-size: 16px; line-height: 1.6; color: var(--muted);">من <b>رایکا</b> هستم، چت‌بات اختصاصی PERSIAN_AI!</p>
            <input type="text" id="nameInput" placeholder="--------------------------&#10;|           اسم شما؟        |&#10;------------------------">
            <button onclick="saveName()">بزن بریم 🚀</button>
        </div>
    </div>
    {% endif %}

    <div class="header-bar">
        <div style="font-weight: bold; color: var(--accent);">رایکا 🤖</div>
        <div style="display:flex; gap: 10px;">
            <div style="background: rgba(34,197,94,0.15); padding: 6px 14px; border-radius: 999px; font-size: 13px;">🪙 <span id="coinCount">{{ coins }}</span> سکه</div>
            {% if is_admin %}
            <a href="/admin" style="background: #ef4444; color: white; padding: 6px 14px; border-radius: 999px; font-size: 13px; text-decoration: none;">پنل مدیریت</a>
            {% endif %}
        </div>
    </div>

    <div class="main-container">
        <div class="chat-feed" id="chatFeed">
            <div class="chat-row assistant">
                <div class="chat-bubble">سلام {% if username %}{{ username }} عزیز{% else %}دوست من{% endif %}! من رایکا هستم. چه کمکی از دستم برمیاد؟ ✨</div>
            </div>
        </div>

        <div class="input-bar">
            <input type="text" id="chatInput" placeholder="پیامت رو اینجا بنویس..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button class="send-btn" onclick="sendMessage()">➤</button>
        </div>
    </div>

    <script>
        const feed = document.getElementById('chatFeed');
        let currentQuestion = "";
        let currentAnswerText = "";

        // بستن مودال و ذخیره اسم
        async function saveName() {
            const name = document.getElementById('nameInput').value.trim();
            if (!name) return;
            await fetch('/set_name', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            });
            document.getElementById('onboardingModal').style.display = 'none';
            // یه پیام خوشامدگویی محلی اضافه میکنیم
            appendBubble(`سلام ${name} عزیز! خوشحالم می‌بینمت.`, 'assistant');
        }

        function appendBubble(text, sender, id="") {
            const row = document.createElement('div');
            row.className = `chat-row ${sender}`;
            row.id = id;
            row.innerHTML = `<div class="chat-bubble">${text}</div>`;
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
            return row.querySelector('.chat-bubble');
        }

        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if(!text) return;
            
            input.value = '';
            currentQuestion = text;
            currentAnswerText = "";

            // پیام کاربر
            appendBubble(text, 'user');

            // حباب در حال فکر کردن (چرخش دایره)
            const bubbleId = 'bot-msg-' + Date.now();
            const botBubble = appendBubble('<div class="spinner"></div>', 'assistant', bubbleId);

            try {
                const response = await fetch('/chat_stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: text})
                });

                if (!response.ok) {
                    if(response.status === 402) throw new Error("سکه کافی نیست!");
                    throw new Error("NetworkError");
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let isFirstChunk = true;

                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, {stream: true});
                    currentAnswerText += chunk;
                    
                    if (isFirstChunk) {
                        botBubble.innerHTML = ""; // حذف Spinner به محض دریافت اولین کلمه
                        isFirstChunk = false;
                    }
                    
                    botBubble.innerHTML = currentAnswerText.replace(/\\n/g, '<br>');
                    feed.scrollTop = feed.scrollHeight;
                }

                // اضافه کردن دکمه‌های بازخورد پس از اتمام تایپ
                addFeedbackButtons(botBubble, currentQuestion, currentAnswerText);

                // آپدیت سکه در UI
                updateCoins();

            } catch (err) {
                if(err.message === "NetworkError" || err.name === "TypeError") {
                    botBubble.innerHTML = "مشکلی در ارتباط با سرور پیش آمد!<br>لطفا اینترنت خود را بررسی کنید!";
                } else {
                    botBubble.innerHTML = err.message;
                }
            }
        }

        function addFeedbackButtons(bubbleElement, q, a) {
            const btns = document.createElement('div');
            btns.className = "action-btns";
            btns.innerHTML = `
                <button onclick="sendFeedback(this, '${encodeURIComponent(q)}', '${encodeURIComponent(a)}', 'like')">👍</button>
                <button class="dislike" onclick="sendFeedback(this, '${encodeURIComponent(q)}', '${encodeURIComponent(a)}', 'dislike')">👎</button>
                <button onclick="copyText('${encodeURIComponent(a)}')">📋 کپی</button>
            `;
            bubbleElement.appendChild(btns);
        }

        async function sendFeedback(btn, q, a, type) {
            btn.parentElement.innerHTML = `<span style="font-size:12px; color:var(--accent);">ثبت شد ✔️</span>`;
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

        async function updateCoins() {
            const res = await fetch('/get_coins');
            const data = await res.json();
            document.getElementById('coinCount').innerText = data.coins;
        }
    </script>
</body>
</html>
"""

# --- قالب پنل ادمین ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8"><title>پنل مدیریت رایکا</title>
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
    <a href="/">🔙 بازگشت به ربات</a>
    <h1>👑 پنل اختصاصی مدیریت</h1>
    
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
    user_id = session.get("uid")
    if not user_id:
        user_id = request.args.get("uid", secrets.token_hex(6))
        session["uid"] = user_id
        
    user_data = get_or_create_user(user_id)
    is_admin = (user_id == "admin_persian_ai")
    
    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        username=user_data["username"],
        coins=user_data["coins"],
        is_admin=is_admin
    )

@app.route("/set_name", methods=["POST"])
def set_name():
    user_id = session.get("uid")
    name = request.json.get("name")
    if user_id and name:
        set_user_name(user_id, name)
    return jsonify({"status": "ok"})

@app.route("/get_coins", methods=["GET"])
def get_coins_route():
    user_id = session.get("uid")
    return jsonify({"coins": get_user_coins(user_id)})

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    user_id = session.get("uid")
    data = request.json
    question = data.get("question", "")
    
    user_data = get_or_create_user(user_id)
    
    if user_id != "admin_persian_ai" and user_data["coins"] < 5:
        return Response("سکه کافی نیست!", status=402)

    def generate():
        history = session.get("history", [])
        success = False
        
        for chunk in answer_question_stream(question, user_data["username"], history):
            # اگر اولین تکه رسید یعنی اتصال موفقه
            success = True 
            yield chunk

        if success:
            deduct_user_coins(user_id, 5)
            # آپدیت حافظه جلسه
            # (در نسخه واقعی استریم، متن کامل باید در یک متغیر ذخیره و بعد به تاریخچه اضافه بشه، 
            # ولی برای سبکی کار اینجا از سمت کلاینت هندل میشه یا تاریخچه موقتیه)

    return Response(generate(), mimetype="text/plain")

@app.route("/feedback", methods=["POST"])
def feedback():
    user_id = session.get("uid")
    data = request.json
    save_feedback(user_id, data.get("question"), data.get("answer"), data.get("type"))
    return jsonify({"status": "saved"})

@app.route("/admin")
def admin_dashboard():
    user_id = session.get("uid")
    if user_id != "admin_persian_ai":
        return "⚠️ شما دسترسی به این بخش ندارید!", 403
    
    stats = get_admin_stats()
    return render_template_string(ADMIN_TEMPLATE, stats=stats)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))