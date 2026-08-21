"""
وب‌سایت هوش مصنوعی «میکرو» - نسخه v1.1.0
تاریخچه چند-گفتگویی، گفتگوی موقت، شخصی‌سازی، آپلود تصویر، آیکون‌های شیشه‌ای،
چت زنده (AJAX)، لوگو، بازخورد، تم‌های رنگی و پنل مدیریت
اجرا: python app.py
"""

import os
import secrets
from datetime import timedelta
from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
from main import (
    answer_question, get_daily_micro_greeting, get_or_create_user,
    get_user_coins, deduct_user_coins,
    get_total_users, save_feedback, get_all_feedback,
    create_conversation, list_conversations, get_turns, add_turn,
    conversation_belongs_to, get_profile, save_profile
)

app = Flask(__name__)

_secret_env = os.getenv("SECRET_KEY")
if not _secret_env:
    print("⚠️ هشدار: متغیر محیطی SECRET_KEY تنظیم نشده! هر بار سرور ری‌استارت بشه، "
          "همه‌ی کاربرها از سیستم خارج می‌شن. حتماً یه مقدار ثابت براش تو Render ست کن.")
app.secret_key = _secret_env or secrets.token_hex(16)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

SITE_NAME = "هوش مصنوعی میکرو"
LOGO_URL = "https://uploadkon.ir/uploads/805818_26ChatGPT-Image-Aug-18-2026-01-02-18-PM.png"
CHANNEL_LINK = "https://ble.ir/micro_ai"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "seyedmahdi_amirmz")
SUPPORT_LINK = "https://ble.ir/admin_persian_Ai"
COIN_PACKAGES = [
    {"coins": 20, "price": "۱۵ هزار تومان", "period": "هفتگی"},
    {"coins": 50, "price": "۴۵ هزار تومان", "period": "هفتگی"},
    {"coins": 70, "price": "۵۵ هزار تومان", "period": "ماهیانه"},
    {"coins": 100, "price": "۹۹ هزار تومان", "period": "ماهیانه"},
]
COST_TEXT_MESSAGE = 0   # فعلاً به یک مناسبت، گفتگوی متنی رایگانه
COST_IMAGE_MESSAGE = 4  # آپلود و تحلیل تصویر
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

        .sidebar {
            width: 250px; background: var(--card); border-left: 1px solid var(--border);
            display: flex; flex-direction: column; padding: 14px; flex-shrink: 0;
        }
        .new-chat-btn, .temp-chat-btn {
            border: none; border-radius: 10px; padding: 10px; font-weight: 700; font-size: 13px;
            cursor: pointer; margin-bottom: 10px;
        }
        .new-chat-btn { background: var(--accent); color: #06210f; }
        .temp-chat-btn { background: var(--bg1); color: var(--text); border: 1px solid var(--border); }
        .temp-chat-btn.active { background: #7c3aed; color: #fff; border-color: #7c3aed; }
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
        .icon-btn {
            background: linear-gradient(145deg, #2a2f3a, #12151a);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 3px 6px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
            color: var(--text); width: 32px; height: 32px; border-radius: 10px; cursor: pointer;
            display: flex; align-items: center; justify-content: center; position: relative;
        }
        .theme-buttons { display: flex; gap: 5px; }
        .theme-btn {
            background: linear-gradient(145deg, #2a2f3a, #12151a);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 3px 6px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
            width: 30px; height: 30px; border-radius: 9px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }
        .theme-btn svg, .icon-btn svg { width: 16px; height: 16px; }
        .coin-add-btn {
            background: linear-gradient(145deg, #34d399, #16a34a);
            border: none; color: #06210f; width: 22px; height: 22px; border-radius: 50%;
            font-weight: 900; font-size: 13px; cursor: pointer; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }
        .settings-menu {
            position: absolute; left: 0; top: 40px; background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 6px; display: none; z-index: 60; min-width: 170px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        }
        .settings-menu.show { display: block; }
        .settings-menu button {
            width: 100%; text-align: right; background: transparent; border: none; color: var(--text);
            padding: 9px 10px; border-radius: 8px; cursor: pointer; font-size: 13px;
        }
        .settings-menu button:hover { background: rgba(255,255,255,0.06); }

        .temp-banner {
            text-align: center; font-size: 12px; padding: 6px; background: rgba(124,58,237,0.15);
            color: #c4b5fd; display: none;
        }
        .temp-banner.show { display: block; }

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
        .msg-actions { display: flex; gap: 10px; padding-right: 4px; align-items: center; }
        .glossy-btn {
            background: linear-gradient(145deg, #2a2f3a, #12151a);
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 3px 6px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
            width: 30px; height: 30px; border-radius: 9px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }
        .glossy-btn svg { width: 15px; height: 15px; }
        .glossy-btn.like.active-like { background: linear-gradient(145deg, #22c55e, #15803d); }
        .glossy-btn.dislike.active-dislike { background: linear-gradient(145deg, #ef4444, #b91c1c); }
        .feedback-toast { font-size: 11.5px; color: var(--accent); }

        .image-preview-bar { display: none; padding: 6px 4px; }
        .image-preview-bar.show { display: flex; align-items: center; gap: 8px; }
        .image-preview-bar img { width: 46px; height: 46px; object-fit: cover; border-radius: 8px; }
        .image-preview-bar button { background: var(--card); border: none; color: var(--muted); border-radius: 8px; padding: 4px 8px; cursor: pointer; font-size: 12px; }

        .input-bar {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 18px; display: flex; align-items: center; padding: 6px 12px; gap: 8px;
        }
        .attach-btn.glossy-btn { width: 36px; height: 36px; border-radius: 12px; }
        .attach-btn.glossy-btn svg { width: 18px; height: 18px; }
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

        /* ---------- مودال شخصی‌سازی ---------- */
        .modal-overlay {
            display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.55);
            z-index: 100; align-items: center; justify-content: center;
        }
        .modal-overlay.show { display: flex; }
        .modal-box {
            background: var(--card); border: 1px solid var(--border); border-radius: 18px;
            padding: 26px; width: 90%; max-width: 420px;
        }
        .modal-box h2 { font-size: 17px; margin-bottom: 18px; }
        .field-group { position: relative; margin-bottom: 20px; }
        .field-group label {
            position: absolute; right: 14px; top: 13px; color: var(--muted); font-size: 13.5px;
            pointer-events: none; transition: 0.15s ease; background: var(--card); padding: 0 4px;
        }
        .field-group input, .field-group textarea {
            width: 100%; background: var(--bg1); border: 1px solid var(--border); border-radius: 10px;
            padding: 13px 12px; color: var(--text); font-size: 14px; font-family: inherit;
        }
        .field-group textarea { min-height: 70px; resize: vertical; }
        .field-group input:focus + label,
        .field-group input:not(:placeholder-shown) + label,
        .field-group textarea:focus + label,
        .field-group textarea:not(:placeholder-shown) + label {
            top: -9px; font-size: 11px; color: var(--accent);
        }
        .privacy-note {
            font-size: 11.5px; color: var(--muted); line-height: 1.8; margin-top: 4px; margin-bottom: 18px;
        }
        .modal-actions { display: flex; gap: 10px; }
        .modal-actions button {
            flex: 1; padding: 12px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; font-size: 13px;
        }
        .modal-save { background: var(--accent); color: #06210f; }
        .modal-cancel { background: var(--bg1); color: var(--text); border: 1px solid var(--border) !important; }

        @media (max-width: 760px) {
            .sidebar { position: fixed; top: 0; bottom: 0; right: 0; z-index: 50; margin-right: -250px; transition: margin-right 0.25s ease; }
            .sidebar.open { margin-right: 0; }
            .sidebar-toggle { display: inline-block; }
        }
    </style>
</head>
<body class="theme-dark" id="pageBody">

    <div class="sidebar" id="sidebar">
        <button class="new-chat-btn" onclick="newChat()">➕ چت جدید</button>
        <button class="temp-chat-btn" id="tempChatBtn" onclick="toggleTempChat()">🕶️ گفتگوی موقت</button>
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
                <div class="user-balance">🪙 <span id="coinBadge">{{ coins }}</span> سکه
                    <button class="coin-add-btn" onclick="openBuyCoins()" title="افزایش اعتبار">+</button>
                </div>
                <div style="position:relative;">
                    <button class="icon-btn" onclick="toggleSettingsMenu()" title="تنظیمات">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z" fill="url(#gradGear)"/><path d="M19.4 13.5c.04-.33.06-.66.06-1s-.02-.67-.06-1l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.4 7.4 0 0 0-1.73-1l-.36-2.54A.5.5 0 0 0 14 2h-3.84a.5.5 0 0 0-.5.44l-.36 2.54c-.63.24-1.2.58-1.73 1l-2.39-.96a.5.5 0 0 0-.6.22L2.66 9.28a.5.5 0 0 0 .12.64L4.8 11.5c-.04.33-.06.66-.06 1s.02.67.06 1l-2.03 1.58a.5.5 0 0 0-.12.64l1.92 3.32c.14.24.42.32.66.22l2.39-.96c.53.42 1.1.76 1.73 1l.36 2.54c.05.25.26.44.5.44H14c.25 0 .46-.19.5-.44l.36-2.54c.63-.24 1.2-.58 1.73-1l2.39.96c.24.1.52.02.66-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.04-1.58z" stroke="#9ca3af" stroke-width="1.3" stroke-linejoin="round" fill="none"/><defs><linearGradient id="gradGear" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#9ca3af"/><stop offset="1" stop-color="#4b5563"/></linearGradient></defs></svg>
                    </button>
                    <div class="settings-menu" id="settingsMenu">
                        <button onclick="openSettings()">⚙️&nbsp; شخصی‌سازی میکرو</button>
                        <button onclick="window.open('{{ support_link }}', '_blank')">🎧&nbsp; پشتیبانی</button>
                    </div>
                </div>
                <div class="theme-buttons">
                    <button class="theme-btn" onclick="setTheme('dark')" title="تیره">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M20 14.5a8.5 8.5 0 1 1-10.5-8.3 6.8 6.8 0 0 0 9.3 9.3c.4-.1.8.3.7.7A8.5 8.5 0 0 1 20 14.5z" fill="url(#gradMoon)"/><defs><linearGradient id="gradMoon" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#cbd5e1"/><stop offset="1" stop-color="#64748b"/></linearGradient></defs></svg>
                    </button>
                    <button class="theme-btn" onclick="setTheme('light')" title="روشن">
                        <svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="4.2" fill="url(#gradSun)"/><g stroke="#fbbf24" stroke-width="1.6" stroke-linecap="round"><path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6"/></g><defs><linearGradient id="gradSun" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#fde68a"/><stop offset="1" stop-color="#f59e0b"/></linearGradient></defs></svg>
                    </button>
                    <button class="theme-btn" onclick="setTheme('colorful')" title="رنگی">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M12 3a9 8 0 1 0 0 18c1.1 0 1.6-.6 1.2-1.4-.3-.6.1-1.3.8-1.3H16a5 4.3 0 0 0 5-4.3C21 7.5 17 3 12 3z" fill="url(#gradPalette)"/><circle cx="8" cy="9" r="1.3" fill="#ef4444"/><circle cx="12" cy="7.5" r="1.3" fill="#3b82f6"/><circle cx="16" cy="9" r="1.3" fill="#eab308"/><circle cx="8.5" cy="13" r="1.3" fill="#22c55e"/><defs><linearGradient id="gradPalette" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#f472b6"/><stop offset="1" stop-color="#7c3aed"/></linearGradient></defs></svg>
                    </button>
                </div>
            </div>
        </div>

        <div class="temp-banner" id="tempBanner">🕶️ گفتگوی موقت فعاله — این چت ذخیره نمی‌شه و امکان لایک/دیس‌لایک نداره</div>

        <div class="join-channel-bar">
            <a href="{{ channel_link }}" target="_blank" class="join-channel-btn">📢 عضویت در کانال میکرو</a>
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
                <span style="font-size:12px; color:var(--muted);">تصویر ضمیمه شد (۴ سکه)</span>
                <button onclick="removeImage()">حذف</button>
            </div>

            <form id="chatForm" onsubmit="return false;">
                <div class="input-bar">
                    <button type="button" class="glossy-btn attach-btn" onclick="document.getElementById('imageInput').click()" title="ضمیمه تصویر">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M21 12.5V7a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v10a4 4 0 0 0 4 4h6" stroke="#9ca3af" stroke-width="1.7" stroke-linecap="round"/><circle cx="8.5" cy="8.5" r="1.5" fill="#9ca3af"/><path d="M4 16l4.5-4.5a2 2 0 0 1 2.8 0L15 15" stroke="#9ca3af" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="18" cy="18" r="4" fill="#22c55e"/><path d="M18 16.3v3.4M16.3 18h3.4" stroke="#06210f" stroke-width="1.6" stroke-linecap="round"/></svg>
                    </button>
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

    <!-- مودال شخصی‌سازی -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal-box">
            <h2>⚙️ شخصی‌سازی میکرو</h2>
            <div class="field-group">
                <input type="text" id="pf_nickname" placeholder=" " value="{{ profile.nickname or user_name }}">
                <label>دوست دارید میکرو شما را چه صدا بزند؟</label>
            </div>
            <div class="field-group">
                <input type="text" id="pf_occupation" placeholder=" " value="{{ profile.occupation }}">
                <label>چه شغلی دارید؟</label>
            </div>
            <div class="field-group">
                <textarea id="pf_about" placeholder=" ">{{ profile.about }}</textarea>
                <label>بیشتر درباره خود بگویید</label>
            </div>
            <div class="privacy-note">
                🔒 اطلاعات شما فقط برای شخصی‌سازی پاسخ‌های میکرو استفاده می‌شه و در اختیار هیچ شخص یا سرویس ثالثی قرار نمی‌گیره.
            </div>
            <div class="modal-actions">
                <button class="modal-cancel" onclick="closeSettings()">انصراف</button>
                <button class="modal-save" onclick="saveSettings()">ذخیره</button>
            </div>
        </div>
    </div>

    <!-- مودال خرید سکه -->
    <div class="modal-overlay" id="buyCoinsModal">
        <div class="modal-box">
            <h2>🪙 افزایش اعتبار</h2>
            <div id="buyCoinsList" style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
                {% for pkg in coin_packages %}
                <div class="feature-card" style="cursor:pointer;" onclick="selectPackage()">
                    <span class="card-text">{{ pkg.coins }} سکه — {{ pkg.price }} ({{ pkg.period }})</span>
                    <span>🪙</span>
                </div>
                {% endfor %}
            </div>
            <div id="buyCoinsNotice" class="privacy-note" style="display:none; color:#fbbf24;"></div>
            <div class="modal-actions">
                <button class="modal-cancel" onclick="closeBuyCoins()">بستن</button>
            </div>
        </div>
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
        let currentConvId = null;
        let selectedImageFile = null;
        let isTempChat = false;
        window.storeAnswers = {};

        const ICONS = {
            like: '<svg viewBox="0 0 24 24" fill="none"><path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3zm0 0l4.5-8a2 2 0 0 1 3.8 1l-.9 5.5H18a2 2 0 0 1 2 2.3l-1.2 7A2 2 0 0 1 16.8 20H10a3 3 0 0 1-3-3" stroke="#9ca3af" stroke-width="1.6" stroke-linejoin="round" fill="url(#gradLike)"/><defs><linearGradient id="gradLike" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#34d399"/><stop offset="1" stop-color="#16a34a"/></linearGradient></defs></svg>',
            dislike: '<svg viewBox="0 0 24 24" fill="none" style="transform:rotate(180deg)"><path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3zm0 0l4.5-8a2 2 0 0 1 3.8 1l-.9 5.5H18a2 2 0 0 1 2 2.3l-1.2 7A2 2 0 0 1 16.8 20H10a3 3 0 0 1-3-3" stroke="#9ca3af" stroke-width="1.6" stroke-linejoin="round" fill="url(#gradDislike)"/><defs><linearGradient id="gradDislike" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#f87171"/><stop offset="1" stop-color="#dc2626"/></linearGradient></defs></svg>',
            copy: '<svg viewBox="0 0 24 24" fill="none"><rect x="8" y="8" width="12" height="12" rx="2.5" fill="url(#gradCopy)"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" stroke="#9ca3af" stroke-width="1.6"/><defs><linearGradient id="gradCopy" x1="0" y1="0" x2="20" y2="20"><stop offset="0" stop-color="#60a5fa"/><stop offset="1" stop-color="#2563eb"/></linearGradient></defs></svg>'
        };

        // ---------- تم ----------
        function setTheme(name) {
            document.body.classList.remove('theme-dark', 'theme-light', 'theme-colorful');
            document.body.classList.add('theme-' + name);
            try { localStorage.setItem('microTheme', name); } catch (e) {}
        }
        (function () {
            try { var saved = localStorage.getItem('microTheme'); if (saved) setTheme(saved); } catch (e) {}
        })();

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

        // ---------- گفتگوی موقت ----------
        function toggleTempChat() {
            isTempChat = !isTempChat;
            document.getElementById('tempChatBtn').classList.toggle('active', isTempChat);
            document.getElementById('tempBanner').classList.toggle('show', isTempChat);
            newChat();
        }

        // ---------- شخصی‌سازی ----------
        function toggleSettingsMenu() {
            document.getElementById('settingsMenu').classList.toggle('show');
        }
        document.addEventListener('click', function (e) {
            const menu = document.getElementById('settingsMenu');
            const btn = e.target.closest('.icon-btn');
            if (menu && menu.classList.contains('show') && !menu.contains(e.target) && !btn) {
                menu.classList.remove('show');
            }
        });
        function openSettings() {
            document.getElementById('settingsMenu').classList.remove('show');
            document.getElementById('settingsModal').classList.add('show');
        }
        function closeSettings() { document.getElementById('settingsModal').classList.remove('show'); }
        function saveSettings() {
            const payload = {
                nickname: document.getElementById('pf_nickname').value.trim(),
                occupation: document.getElementById('pf_occupation').value.trim(),
                about: document.getElementById('pf_about').value.trim()
            };
            fetch('/api/profile', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }).then(function () { closeSettings(); });
        }

        // ---------- خرید سکه ----------
        function openBuyCoins() {
            document.getElementById('buyCoinsNotice').style.display = 'none';
            document.getElementById('buyCoinsModal').classList.add('show');
        }
        function closeBuyCoins() { document.getElementById('buyCoinsModal').classList.remove('show'); }
        function selectPackage() {
            const notice = document.getElementById('buyCoinsNotice');
            notice.innerText = 'درحال حاضر خرید سکه تنها از بخش پشتیبانی انجام می‌شود!';
            notice.style.display = 'block';
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
                img.src = imageDataUrl; img.className = 'attached';
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
            let actionsHtml = `<button class="glossy-btn" onclick="copyMsg(${id})" title="کپی">${ICONS.copy}</button>`;
            if (!isTempChat) {
                actionsHtml = `
                    <button class="glossy-btn like" onclick="giveFeedback(${id}, 'like')" id="like-${id}" title="لایک">${ICONS.like}</button>
                    <button class="glossy-btn dislike" onclick="giveFeedback(${id}, 'dislike')" id="dislike-${id}" title="دیس‌لایک">${ICONS.dislike}</button>
                    ` + actionsHtml + `
                    <span class="feedback-toast" id="toast-${id}"></span>`;
            }
            row.innerHTML = `
                <div class="assistant-wrap">
                    <div class="chat-bubble" id="bubble-${id}"><div class="typing-dots"><span></span><span></span><span></span></div></div>
                    <div class="msg-actions" id="actions-${id}" style="display:none;">${actionsHtml}</div>
                </div>`;
            feed.appendChild(row);
            feed.scrollTop = feed.scrollHeight;
        }

        function typeWriter(id, fullText, done) {
            const el = document.getElementById('bubble-' + id);
            let i = 0; const speed = 12;
            function step() {
                if (i <= fullText.length) {
                    el.innerText = fullText.slice(0, i);
                    feed.scrollTop = feed.scrollHeight;
                    i += 3; setTimeout(step, speed);
                } else { el.innerText = fullText; if (done) done(); }
            }
            step();
        }

        function sendPrompt(text) { input.value = text; sendMessage(); }

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
            if (currentConvId && !isTempChat) formData.append('conversation_id', currentConvId);
            if (selectedImageFile) formData.append('image', selectedImageFile);
            formData.append('temporary', isTempChat ? '1' : '0');
            removeImage();

            fetch('/api/ask', { method: 'POST', body: formData })
            .then(function (res) { if (!res.ok) throw new Error('server'); return res.json(); })
            .then(function (data) {
                if (data.error) {
                    document.getElementById('bubble-' + id).innerText = data.error;
                    sendBtn.disabled = false; return;
                }
                if (data.conversation_id && !currentConvId && !isTempChat) {
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

        input.addEventListener('keydown', function (e) { if (e.key === 'Enter') sendMessage(); });

        function copyMsg(id) { navigator.clipboard.writeText(window.storeAnswers[id] || ''); }

        function giveFeedback(id, verdict) {
            fetch('/api/feedback', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answer: window.storeAnswers[id] || '', verdict: verdict })
            });
            document.getElementById('like-' + id).classList.remove('active-like');
            document.getElementById('dislike-' + id).classList.remove('active-dislike');
            document.getElementById(verdict + '-' + id).classList.add('active-' + verdict);
            const toast = document.getElementById('toast-' + id);
            if (toast) { toast.innerText = 'از بازخوردتان صمیمانه متشکریم! 🙏'; setTimeout(function () { toast.innerText = ''; }, 4000); }
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
            if (isTempChat) toggleTempChat();
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
    profile = get_profile(user_id)

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        logo=LOGO_URL,
        coins=get_user_coins(user_id),
        admin=is_admin(),
        channel_link=CHANNEL_LINK,
        support_link=SUPPORT_LINK,
        coin_packages=COIN_PACKAGES,
        greeting=get_daily_micro_greeting(profile.get("nickname") or session.get("user_name")),
        profile=profile,
        user_name=session.get("user_name", ""),
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


@app.route("/api/profile", methods=["POST"])
def api_profile():
    if "user_name" not in session:
        return jsonify({"ok": False}), 400
    data = request.get_json(silent=True) or {}
    save_profile(
        get_user_id(),
        (data.get("nickname") or "").strip(),
        (data.get("occupation") or "").strip(),
        (data.get("about") or "").strip(),
    )
    return jsonify({"ok": True})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    if "user_name" not in session:
        return jsonify({"error": "لطفاً اول اسمت رو وارد کن."}), 400

    question = (request.form.get("question") or "").strip()
    conv_id = request.form.get("conversation_id")
    is_temp = request.form.get("temporary") == "1"
    image_file = request.files.get("image")

    if not question and not image_file:
        return jsonify({"error": "پیام خالیه!"}), 400

    user_id = get_user_id()
    user_name = session.get("user_name", "کاربر")
    profile = get_profile(user_id)
    cost = COST_IMAGE_MESSAGE if image_file else COST_TEXT_MESSAGE
    coins = get_user_coins(user_id)

    if not is_admin() and coins < cost:
        return jsonify({
            "error": "⚠️ سکه شما کافی نیست! برای افزایش موجودی از دکمه‌ی «افزایش اعتبار» تو ربات بله استفاده کن.",
        })

    history = []
    if not is_temp:
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
    else:
        conv_id = None

    image_bytes = None
    image_mime = None
    if image_file:
        image_bytes = image_file.read()
        if len(image_bytes) > MAX_IMAGE_MB * 1024 * 1024:
            return jsonify({"error": f"⚠️ حجم تصویر بیشتر از {MAX_IMAGE_MB} مگابایته."}), 400
        image_mime = image_file.mimetype or "image/jpeg"

    answer, success = answer_question(question, user_name, history, image_bytes, image_mime, profile)

    if success and not is_admin() and cost > 0:
        deduct_user_coins(user_id, cost)

    if not is_temp and conv_id:
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
