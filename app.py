"""
وب‌سایت هوش مصنوعی «میکرو» - نسخه کامل با سایدبار تاریخچه چت، آپلود تصویر،
چت زنده (AJAX)، لوگو، بازخورد، تم‌های رنگی و پنل مدیریت
اجرا: python app.py
"""

import os
import secrets
from datetime import timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
from main import (
    answer_question, get_daily_micro_greeting, get_or_create_user,
    get_user_coins, deduct_user_coins, claim_channel_bonus,
    get_total_users, save_feedback, get_all_feedback,
    create_conversation, list_conversations, get_turns, add_turn,
    conversation_belongs_to
)

app = Flask(__name__)

_secret_env = os.getenv("SECRET_KEY")
if not _secret_env:
    print("⚠️ هشدار: متغیر محیطی SECRET_KEY تنظیم نشده! هر بار که سرور ری‌استارت بشه، "
          "همه‌ی کاربرها از سیستم خارج می‌شن و session‌شون پاک می‌شه. "
          "حتماً یه مقدار ثابت براش تو تنظیمات Render ست کن.")
app.secret_key = _secret_env or secrets.token_hex(16)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"
LOGO_URL = "https://uploadkon.ir/uploads/805818_26ChatGPT-Image-Aug-18-2026-01-02-18-PM.png"
CHANNEL_LINK = "https://ble.ir/micro_ai"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")
COST_PER_MESSAGE = 1
CHANNEL_DWELL_SECONDS = 15
MAX_IMAGE_MB = 6


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
# قالب اصلی چت
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
        body.theme-light {
            --bg1: #f6f8fa; --bg2: #ffffff; --card: #eaeef2; --border: rgba(0,0,0,0.1);
            --accent: #16a34a; --text: #1f2328; --muted: #656d76;
        }
        body.theme-colorful {
            --bg1: #1a0b2e; --bg2: #2b1055; --card: #3b1b6d; --border: rgba(255,255,255,0.15);
            --accent: #ec4899; --text: #ffffff; --muted: #d8b4fe;
        }
        body {
            background: radial-gradient(circle at top, var(--bg2), var(--bg1));
            color: var(--text); min-height: 100vh; display: flex;
        }

        /* ----- سایدبار تاریخچه چت ----- */
        .sidebar {
            width: 250px; background: var(--card); border-left: 1px solid var(--border);
            display: flex; flex-direction: column; padding: 14px; flex-shrink: 0;
            transition: margin-right 0.25s ease;
        }
        .sidebar.collapsed { margin-right: -250px; }
        .new-chat-btn {
            background: var(--accent); color: #06210f; border: none; border-radius: 10px;
            padding: 10px; font-weight: 700; font-size: 13px; cursor: pointer; margin-bottom: 14px;
        }
        .conv-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .conv-item {
            padding: 9px 12px; border-radius: 9px; font-size: 12.5px; cursor: pointer;
            color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .conv-item:hover, .conv-item.active { background: rgba(255,255,255,0.06); color: var(--text); }
        .sidebar-toggle {
            display: none; background: var(--card); border: 1px solid var(--border); color: var(--text);
            border-radius: 8px; padding: 6px 10px; cursor: pointer; font-size: 13px;
        }

        .app-body { flex: 1; display: flex; flex-direction: column; min-width: 0; }
        .header-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 20px; border-bottom: 1px solid var(--border);
        }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand img { width: 34px; height: 34px; border-radius: 9px; }
        .brand span { font-weight: 800; font-size: 15px; }
        .user-balance {
            background: rgba(34,197,94,0.15); border: 1px solid var(--accent);
            color: var(--accent); padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 700;
        }
        .header-right { display: flex; align-items: center; gap: 10px; }
        .admin-link { color: var(--muted); font-size: 12px; text-decoration: none; }
        .theme-buttons { display: flex; gap: 5px; }
        .theme-btn {
            background: var(--bg1); border: 1px solid var(--border);
            color: var(--text); padding: 4px 8px; border-radius: 8px; font-size: 11px; cursor: pointer;
        }

        .join-channel-bar { display: flex; justify-content: center; padding: 8px; }
        .join-channel-btn {
            background: linear-gradient(135deg, #0ea5e9, #2563eb);
            color: #fff; text-decoration: none; padding: 7px 16px; border-radius: 999px;
            font-size: 12px; font-weight: 700;
        }

        .main-container { max-width: 780px; width: 100%; margin: 0 auto; padding: 16px 20px; flex: 1; display: flex; flex-direction: column; min-height: 0; }

        .hero-banner { text-align: center; margin: 15px 0 25px; }
        .hero-rocket { font-size: 44px; margin-bottom: 10px; animation: float 3s ease-in-out infinite; }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        .hero-title { font-size: 24px; font-weight: 800; color: var(--accent); margin-bottom: 20px; }
        .cards-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; }
        .feature-card {
            background: var(--card); border: 1px solid var(--border);
            padding: 16px; border-radius: 16px; cursor: pointer;
            display: flex; align-items: center; justify-content: space-between; transition: 0.2s;
        }
        .feature-card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .card-text { font-size: 13px; font-weight: 600; }

        .chat-feed { flex: 1; display: flex; flex-direction: column; gap: 14px; margin-bottom: 15px; overflow-y: auto; min-height: 0; }
        .chat-row { display: flex; gap: 10px; }
        .chat-row.user { justify-content: flex-end; }
        .chat-bubble { max-width: 82%; padding: 12px 18px; border-radius: 16px; font-size: 14px; line-height: 1.85; white-space: pre-wrap; }
        .chat-bubble img.attached { max-width: 220px; border-radius: 10px; display: block; margin-bottom: 8px; }
        .chat-row.user .chat-bubble { background: #2563eb; color: #fff; border-bottom-left-radius: 4px; }
        .chat-row.assistant .chat-bubble { background: var(--card); border: 1px solid var(--border); border-bottom-right-radius: 4px; min-height: 20px; }

        .typing-dots { display: inline-flex; gap: 4px; align-items: center; height: 14px; }
        .typing-dots span {
            width: 6px; height: 6px; border-radius: 50%; background: var(--muted);
            animation: dotBounce 1.1s infinite ease-in-out;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.15s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.3s; }
        @keyframes dotBounce {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
            30% { transform: translateY(-5px); opacity: 1; }
        }

        .assistant-wrap { display: flex; flex-direction: column; gap: 6px; max-width: 82%; }
        .msg-actions { display: flex; gap: 8px; padding-right: 4px; }
        .msg-actions button {
            background: transparent; border: none; color: var(--muted); cursor: pointer; font-size: 13px;
        }
        .msg-actions button.active-like { color: #22c55e; }
        .msg-actions button.active-dislike { color: #ef4444; }

        .image-preview-bar { display: none; padding: 6px 4px; }
        .image-preview-bar.show { display: flex; align-items: center; gap: 8px; }
        .image-preview-bar img { width: 46px; height: 46px; object-fit: cover; border-radius: 8px; }
        .image-preview-bar button { background: var(--card); border: none; color: var(--muted); border-radius: 8px; padding: 4px 8px; cursor: pointer; font-size: 12px; }

        .input-bar {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 18px; display: flex; align-items: center; padding: 6px 12px; gap: 8px;
        }
        .attach-btn {
            background: transparent; border: none; color: var(--muted); font-size: 19px; cursor: pointer; padding: 4px;
        }
        .input-bar input {
            flex: 1; background: transparent; border: none; outline: none;
            color: var(--text); font-size: 15px; padding: 10px 4px;
        }
        .send-btn {
            background: var(--accent); border: none; width: 40px; height: 40px;
            border-radius: 50%; color: #000; font-size: 18px; cursor: pointer; flex-shrink: 0;
        }
        .send-btn:disabled { opacity: 0.5; }

        .error-msg { background: #3a1420; border: 1px solid #ef4444; color: #ffb3c0; padding: 12px 16px; border-radius: 12px; font-size: 13px; text-align: center; }

        footer {
            text-align: center; padding: 15px 20px; font-size: 11px;
            color: var(--muted); border-top: 1px solid var(--border);
            display: flex; justify-content: space-around; flex-wrap: wrap; gap: 10px;
        }
        footer a { color: var(--muted); text-decoration: none; }
        footer a:hover { color: var(--accent); }

        @media (max-width: 760px) {
            .sidebar { position: fixed; top: 0; bottom: 0; right: 0; z-index: 50; margin-right: -250px; }
            .sidebar.open { margin-right: 0; }
            .sidebar-toggle { display: inline-block; }
        }
    </style>
</head>
<body class="theme-dark" id="pageBody">

    <div class="sidebar" id="sidebar">
        <button class="new-chat-btn" onclick="newChat()">➕ چت جدید</button>
        <div class="conv-list" id="convList"></div>
    </div>

    <div class="app-body">
        <div class="header-bar">
            <div style="display:flex; align-items:center; gap:8px;">
                <button class="sidebar-toggle" onclick="toggleSidebar()">☰</button>
                <div class="brand">
                    <img src="{{ logo }}" id="brandLogo" alt="میکرو">
                    <span>میکرو</span>
                </div>
            </div>
            <div class="header-right">
                {% if admin %}<a class="admin-link" href="/admin">📊 پنل مدیریت</a>{% endif %}
                <div class="user-balance">🪙 <span id="coinBadge">{{ coins }}</span> سکه</div>
                <div class="theme-buttons">
                    <button class="theme-btn" onclick="setTheme('dark')">🌙</button>
                    <button class="theme-btn" onclick="setTheme('light')">☀️</button>
                    <button class="theme-btn" onclick="setTheme('colorful')">🎨</button>
                </div>
            </div>
        </div>

        <div class="join-channel-bar">
            <a href="{{ channel_link }}" target="_blank" id="channelLink" class="join-channel-btn">📢 عضویت در کانال میکرو (+۲۵ سکه)</a>
        </div>

        <div class="main-container">
            <div class="hero-banner" id="heroBanner">
                <div class="hero-rocket">🚀</div>
                <div class="hero-title">{{ greeting }}</div>
                <div class="cards-grid">
                    <div class="feature-card" onclick="sendPrompt('بمب انرژی و انگیزه روزانه برای پیشرفت')">
                        <span class="card-text">بمب انرژی و انگیزه روزانه</span><span>🔥</span>
                    </div>
                    <div class="feature-card" onclick="sendPrompt('چند دانستنی و گیم جذاب به من معرفی کن')">
                        <span class="card-text">دنیای گیم و سرگرمی</span><span>🎮</span>
                    </div>
                    <div class="feature-card" onclick="sendPrompt('ایده‌های ناب برنامه‌نویسی و هوش مصنوعی بده')">
                        <span class="card-text">ایده‌های ناب برنامه‌نویسی</span><span>🚀</span>
                    </div>
                    <div class="feature-card" onclick="sendPrompt('شگفتی‌ها و اسرار علمی نجوم و فضا را بگو')">
                        <span class="card-text">اسرار علمی نجوم و فضا</span><span>🌌</span>
                    </div>
                </div>
            </div>

            <div class="chat-feed" id="chatFeed"></div>
            <div id="errorBox"></div>

            <div class="image-preview-bar" id="imagePreviewBar">
                <img id="imagePreviewThumb" src="">
                <span style="font-size:12px; color:var(--muted);">تصویر ضمیمه شد</span>
                <button onclick="removeImage()">حذف</button>
            </div>

            <form id="chatForm" onsubmit="return false;">
                <div class="input-bar">
                    <button type="button" class="attach-btn" onclick="document.getElementById('imageInput').click()">📎</button>
                    <input type="file" id="imageInput" accept="image/*" style="display:none;" onchange="onImageSelected(event)">
                    <input type="text" id="chatInput" placeholder="اینجا با من گپ بزن..." autofocus>
                    <button type="submit" class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
                </div>
            </form>
        </div>

        <footer>
            <span>جهت ارتباط با پشتیبان (بله): <a href="https://ble.ir/admin_persian_ai" target="_blank">@admin_persian_ai</a></span>
            <span>کانال توسعه‌دهنده (بله): <a href="https://ble.ir/persian_Ai" target="_blank">@persian_Ai</a></span>
        </footer>
    </div>

    <script>
        const feed = document.getElementById('chatFeed');
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const coinBadge = document.getElementById('coinBadge');
        const errorBox = document.getElementById('errorBox');
        const heroBanner = document.getElementById('heroBanner');
        const imageInput = document.getElementById('imageInput');
        const imagePreviewBar = document.getElementById('imagePreviewBar');
        const imagePreviewThumb = document.getElementById('imagePreviewThumb');
        let msgCounter = 0;
        let claimed = false;
        let currentConvId = null;
        let selectedImageFile = null;
        window.storeAnswers = {};

        // ---------- تم ----------
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

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
        }

        // ---------- تصویر ضمیمه ----------
        function onImageSelected(e) {
            const file = e.target.files[0];
            if (!file) return;
            selectedImageFile = file;
            const reader = new FileReader();
            reader.onload = function (ev) {
                imagePreviewThumb.src = ev.target.result;
                imagePreviewBar.classList.add('show');
            };
            reader.readAsDataURL(file);
        }
        function removeImage() {
            selectedImageFile = null;
            imageInput.value = '';
            imagePreviewBar.classList.remove('show');
        }

        // ---------- رندر پیام‌ها ----------
        function addUserBubble(text, imageDataUrl) {
            const row = document.createElement('div');
            row.className = 'chat-row user';
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble';
            if (imageDataUrl) {
                const img = document.createElement('img');
                img.src = imageDataUrl;
                img.className = 'attached';
                bubble.appendChild(img);
            }
            const span = document.createElement('span');
            span.innerText = text;
            bubble.appendChild(span);
            row.appendChild(bubble);
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
        }

        function addAssistantBubble(id) {
            const row = document.createElement('div');
            row.className = 'chat-row assistant';
            row.innerHTML = `
                <div class="assistant-wrap">
                    <div class="chat-bubble" id="bubble-${id}"><div class="typing-dots"><span></span><span></span><span></span></div></div>
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

        // ---------- ارسال پیام ----------
        function sendPrompt(text) {
            input.value = text;
            sendMessage();
        }

        function sendMessage() {
            const text = input.value.trim();
            if (!text && !selectedImageFile) return;

            heroBanner.style.display = 'none';
            input.value = '';
            sendBtn.disabled = true;
            errorBox.innerHTML = '';

            const imgDataUrl = imagePreviewBar.classList.contains('show') ? imagePreviewThumb.src : null;
            addUserBubble(text, imgDataUrl);

            const id = ++msgCounter;
            addAssistantBubble(id);

            const formData = new FormData();
            formData.append('question', text);
            if (currentConvId) formData.append('conversation_id', currentConvId);
            if (selectedImageFile) formData.append('image', selectedImageFile);
            removeImage();

            fetch('/api/ask', { method: 'POST', body: formData })
            .then(function (res) {
                if (!res.ok) throw new Error('server');
                return res.json();
            })
            .then(function (data) {
                if (data.error) {
                    document.getElementById('bubble-' + id).innerText = data.error;
                    sendBtn.disabled = false;
                    return;
                }
                if (data.conversation_id && !currentConvId) {
                    currentConvId = data.conversation_id;
                    loadConversations();
                }
                window.storeAnswers[id] = data.answer;
                if (typeof data.coins === 'number') coinBadge.innerText = data.coins;
                typeWriter(id, data.answer, function () {
                    document.getElementById('actions-' + id).style.display = 'flex';
                    sendBtn.disabled = false;
                });
            })
            .catch(function () {
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
            fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answer: window.storeAnswers[id] || '', verdict: verdict })
            });
            document.getElementById('like-' + id).classList.remove('active-like');
            document.getElementById('dislike-' + id).classList.remove('active-dislike');
            document.getElementById(verdict + '-' + id).classList.add('active-' + verdict);
        }

        // ---------- سایدبار تاریخچه چت ----------
        function newChat() {
            currentConvId = null;
            feed.innerHTML = '';
            heroBanner.style.display = 'block';
            document.querySelectorAll('.conv-item').forEach(function (el) { el.classList.remove('active'); });
            document.getElementById('sidebar').classList.remove('open');
        }

        function loadConversations() {
            fetch('/api/conversations').then(function (r) { return r.json(); }).then(function (data) {
                const list = document.getElementById('convList');
                list.innerHTML = '';
                (data.conversations || []).forEach(function (c) {
                    const item = document.createElement('div');
                    item.className = 'conv-item' + (c.id === currentConvId ? ' active' : '');
                    item.innerText = c.title;
                    item.onclick = function () { openConversation(c.id); };
                    list.appendChild(item);
                });
            });
        }

        function openConversation(id) {
            currentConvId = id;
            document.querySelectorAll('.conv-item').forEach(function (el) { el.classList.remove('active'); });
            fetch('/api/conversations/' + id).then(function (r) { return r.json(); }).then(function (data) {
                feed.innerHTML = '';
                const turns = data.turns || [];
                if (turns.length) heroBanner.style.display = 'none';
                turns.forEach(function (t) {
                    addUserBubble(t.q, null);
                    const id2 = ++msgCounter;
                    addAssistantBubble(id2);
                    document.getElementById('bubble-' + id2).innerText = t.a;
                    document.getElementById('actions-' + id2).style.display = 'flex';
                    window.storeAnswers[id2] = t.a;
                });
                loadConversations();
                document.getElementById('sidebar').classList.remove('open');
            });
        }

        loadConversations();

        // ---------- تشخیص عضویت در کانال با تایمر حضور (Visibility API) ----------
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
        greeting=get_daily_micro_greeting(session.get("user_name")),
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

    question = (request.form.get("question") or "").strip()
    conv_id = request.form.get("conversation_id")
    image_file = request.files.get("image")

    if not question and not image_file:
        return jsonify({"error": "پیام خالیه!"}), 400

    user_id = get_user_id()
    user_name = session.get("user_name", "کاربر")
    coins = get_user_coins(user_id)

    if not is_admin() and coins < COST_PER_MESSAGE:
        return jsonify({
            "error": "⚠️ سکه شما کافی نیست! برای افزایش موجودی از دکمه‌ی «افزایش اعتبار» تو ربات بله استفاده کن.",
        })

    # مدیریت مکالمه: اگه از قبل انتخاب نشده، یه مکالمه‌ی جدید بساز
    if conv_id:
        try:
            conv_id = int(conv_id)
        except ValueError:
            conv_id = None
        if conv_id and not conversation_belongs_to(conv_id, user_id):
            conv_id = None
    if not conv_id:
        conv_id = create_conversation(user_id)

    history = get_turns(conv_id)

    image_bytes = None
    image_mime = None
    if image_file:
        image_bytes = image_file.read()
        if len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
            return jsonify({"error": f"⚠️ حجم تصویر بیشتر از {MAX_IMAGE_MB} مگابایته."}), 400
        image_mime = image_file.mimetype or "image/jpeg"

    answer, success = answer_question(question, user_name, history, image_bytes, image_mime)

    if success and not is_admin():
        deduct_user_coins(user_id, COST_PER_MESSAGE)

    add_turn(conv_id, question or "[تصویر ارسال شد]", answer, had_image=bool(image_file))

    return jsonify({"answer": answer, "coins": get_user_coins(user_id), "conversation_id": conv_id})


@app.route("/api/conversations", methods=["GET"])
def api_conversations():
    if "user_name" not in session:
        return jsonify({"conversations": []})
    return jsonify({"conversations": list_conversations(get_user_id())})


@app.route("/api/conversations/<int:conv_id>", methods=["GET"])
def api_conversation_detail(conv_id):
    if "user_name" not in session:
        return jsonify({"turns": []}), 400
    user_id = get_user_id()
    if not conversation_belongs_to(conv_id, user_id):
        return jsonify({"turns": []}), 403
    return jsonify({"turns": get_turns(conv_id)})


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
