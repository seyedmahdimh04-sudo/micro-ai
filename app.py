"""
وب‌سایت محلی چت‌بات خبری «میکرو»
------------------------------------
این فایل یک رابط وب ساده می‌سازد تا به‌جای تایپ سؤال در ترمینال،
بتوانید از طریق مرورگر با چت‌بات صحبت کنید.

اجرا:
    python app.py

بعد از اجرا، مرورگر را باز کنید و بروید به:
    http://127.0.0.1:5000
"""

from flask import Flask, request, render_template_string
from urllib.parse import quote
from main import answer_question

app = Flask(__name__)

SITE_NAME = "هوش مصنوعی میکرو"

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
        header {
            text-align: center;
            padding: 30px 20px 10px;
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
        form {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
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
        .loading {
            text-align: center;
            color: #999;
            padding: 20px;
        }
        .error {
            background: #4a1e2a;
            color: #ffb3c0;
            padding: 16px;
            border-radius: 10px;
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
            margin-bottom: 30px;
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
        .image-result {
            text-align: center;
        }
        .image-result img {
            max-width: 100%;
            border-radius: 14px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <header>
        <h1>🤖 {{ site_name }}</h1>
        <p>چت‌بات خبری هوشمند و ساخت تصویر با هوش مصنوعی</p>
    </header>

    <div class="container">
        <div class="tabs">
            <a href="/" class="tab {{ 'active' if mode == 'chat' else '' }}">💬 پرسش و پاسخ</a>
            <a href="/image" class="tab {{ 'active' if mode == 'image' else '' }}">🎨 ساخت تصویر</a>
        </div>

        {% if mode == 'chat' %}
        <form method="POST" action="/">
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
        <form method="POST" action="/image">
            <input type="text" name="prompt" placeholder="مثلاً: یک گربه فضانورد روی ماه" value="{{ prompt or '' }}" autofocus required>
            <button type="submit">ساخت تصویر</button>
        </form>

        {% if prompt %}
            <div class="question">🎨 {{ prompt }}</div>
            <div class="image-result">
                <p style="color:#999; font-size:13px;">⏳ ساخت تصویر ممکن است تا ۲۰ ثانیه طول بکشد...</p>
                <img src="{{ image_url }}" alt="{{ prompt }}"
                     onerror="this.onerror=null; this.style.display='none'; document.getElementById('img-error').style.display='block';">
                <div id="img-error" class="error" style="display:none;">
                    ⚠️ تصویر بارگذاری نشد. چند ثانیه صبر کن و دوباره امتحان کن، یا پرامپت را ساده‌تر بنویس.
                </div>
            </div>
        {% endif %}
        {% endif %}
    </div>

    <footer>ساخته شده توسط تیم فنی persian_ai</footer>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    question = None
    answer = None
    error = None

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            try:
                answer = answer_question(question)
            except Exception as e:
                error = str(e)

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="chat",
        question=question,
        answer=answer,
        error=error,
    )


@app.route("/image", methods=["GET", "POST"])
def image_page():
    prompt = None
    image_url = None

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if prompt:
            encoded_prompt = quote(prompt)
            image_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width=768&height=768&nologo=true&seed=42"
            )

    return render_template_string(
        PAGE_TEMPLATE,
        site_name=SITE_NAME,
        mode="image",
        prompt=prompt,
        image_url=image_url,
    )


if __name__ == "__main__":
    import os as _os
    port = int(_os.environ.get("PORT", 5000))
    print("=" * 50)
    print(f"🌐 {SITE_NAME} در حال اجراست...")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=port)
