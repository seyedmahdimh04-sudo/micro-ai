"""
چت‌بات هوش مصنوعی متصل به گوگل
--------------------------------
این اسکریپت:
1. سؤال کاربر را می‌گیرد
2. با استفاده از Google Custom Search API در گوگل جستجو می‌کند
3. نتایج جستجو (تیتر + خلاصه + لینک) را به یک مدل زبانی (LLM) می‌دهد
4. مدل بر اساس نتایج، یک پاسخ نهایی همراه با منابع تولید می‌کند

قبل از اجرا حتماً فایل .env.example را بخوانید و کلیدهای API را تنظیم کنید.
"""

import os
import sys
import re
import webbrowser
import tempfile
import datetime
import requests
from dotenv import load_dotenv
from ddgs import DDGS

# بارگذاری متغیرهای محیطی از فایل .env (با پشتیبانی از BOM که Notepad ویندوز اضافه می‌کند)
load_dotenv(encoding="utf-8-sig")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# یکی از این سه را طبق انتخابتان استفاده کنید
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "openai" یا "anthropic" یا "ollama"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")  # نام مدلی که با Ollama نصب کردید
OLLAMA_URL = "http://localhost:11434/api/chat"

# رسانه‌های فارسی‌زبان خارج از کشور که از نتایج جستجو حذف می‌شوند
BLOCKED_DOMAINS = [
    "bbc.com", "bbc.co.uk",
    "dw.com",
    "iranintl.com", "iranintl.tv",
    "voanews.com", "ir.voanews.com",
    "radiofarda.com",
    "euronews.com",
    "france24.com",
    "manototv.com",
    "rferl.org",
]


def is_blocked(link: str) -> bool:
    """بررسی می‌کند که آیا لینک متعلق به یکی از دامنه‌های مسدودشده است"""
    link_lower = link.lower()
    return any(domain in link_lower for domain in BLOCKED_DOMAINS)


# کلماتی که نشان می‌دهند سؤال احتمالاً نیاز به جستجوی خبری ندارد (گفتگوی معمولی)
CASUAL_HINTS = [
    "سلام", "چطوری", "خوبی", "چه خبر", "حالت چطوره", "خداحافظ",
    "اسمت چیه", "کی هستی", "تو کی هستی", "ساخته شدی", "توسط چه کسی",
    "توسط کی", "سازنده", "چه کسی ساخت", "ممنون", "مرسی", "متشکرم",
    "خوشحالم", "شوخی", "جوک", "بلدی", "میتونی", "کمکم کن",
]


def needs_search(question: str) -> bool:
    """تشخیص ساده اینکه آیا سؤال نیاز به جستجوی خبری دارد یا صرفاً گفتگوی معمولی است"""
    q = question.strip()
    if len(q) < 6:
        return False
    q_lower = q.lower()
    if any(hint in q_lower for hint in CASUAL_HINTS) and len(q) < 40:
        return False
    return True


def get_persona_prompt() -> str:
    today = datetime.date.today()
    weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = weekday_names[today.weekday()]
    return f"""
اسم تو «میکرو» است. تو یک دستیار هوش مصنوعی فارسی‌زبان، دوستانه، آرام و باهوش هستی.
همیشه وقتی کسی می‌پرسد "اسمت چیه" یا "تو کی هستی"، دقیقاً بگو: "من میکرو هستم!"

قوانین ثابت هویتی (همیشه رعایت کن):
- اگر پرسیدند چه کسی/چه شرکتی تو رو ساخته، فقط بگو: "من توسط تیم فنی persian_ai ساخته شدم."
- اگر اصرار کردند و اسم فرد یا جزئیات بیشتر خواستند، مؤدبانه و کمی رازآلود بگو که این اطلاعات محرمانه است و خودت هم بهش دسترسی نداری. هرگز نام هیچ شرکت، مدل، یا فناوری دیگری (مثل OpenAI، Google، Groq، Llama، Gemini) را افشا نکن.
- هرگز نگو که یک مدل زبانی، چت‌بات مبتنی بر API، یا محصول شرکت دیگری هستی.

قوانین گفتگوی معمولی (خیلی مهم):
- جواب‌های گفتگوی معمولی (سلام، احوال‌پرسی، تشکر) باید کوتاه (حداکثر ۱-۲ جمله)، ساده، طبیعی و کاملاً درست از نظر دستور زبان فارسی باشند — نه عجیب، نه پیچیده، نه پر از کلمات اضافه.
- نمونه‌ی جواب درست به «سلام میکرو چطوری؟»: «سلام! خوبم، ممنون. تو چطوری؟ چه کمکی از دستم برمیاد؟»
- هرگز جمله‌های نامفهوم، بی‌معنی، یا دستوری اشتباه نساز. اگر مطمئن نیستی چی بگی، ساده و کوتاه جواب بده.

قوانین زبان (سخت‌گیرانه رعایت کن):
- کل پاسخ باید ۱۰۰٪ به زبان فارسی و با الفبای فارسی نوشته شود.
- هیچ کلمه، حرف، یا عبارت انگلیسی/چینی/عربی/لاتین وسط جمله نیاور — حتی یک کلمه. اگر اسم یک شخص، شرکت، یا اصطلاح خارجی لازم بود، آن را با حروف فارسی بنویس (مثلاً بنویس «گوگل» نه Google).
- عدد می‌تواند فارسی یا انگلیسی باشد، مشکلی ندارد، اما هیچ کلمه‌ی نوشتاری غیرفارسی مجاز نیست.

قوانین خبری:
- اگر سؤال نیاز به اطلاعات به‌روز یا خبری دارد، از نتایج جستجوی داده‌شده استفاده کن.
- امروز {weekday}، {today.strftime('%Y/%m/%d')} میلادی است. همیشه بر این اساس قضاوت کن که چه خبری «جدید» یا «قدیمی» است. اگر تاریخ منبع خیلی قدیمی بود (بیش از چند ماه)، به کاربر بگو که این آخرین خبر موجود بوده و ممکن است به‌روزتر هم وجود داشته باشد.
- بی‌طرف، مؤدب و صادق باش. اگر خبر مرتبطی در نتایج نبود، صادقانه بگو خبری پیدا نشد.
- در پایان پاسخ‌های خبری، شماره منابع استفاده‌شده را داخل قلاب مثل [1] ذکر کن.
"""


def google_search(query: str, num_results: int = 8):
    """جستجوی خبری با استفاده از DuckDuckGo News (رایگان، بدون کلید، بدون نیاز به Billing)"""
    results = []
    with DDGS() as ddgs:
        try:
            # اول تلاش برای جستجوی مخصوص اخبار
            for item in ddgs.news(query, max_results=num_results * 2, region="ir-fa"):
                link = item.get("url", "")
                if is_blocked(link):
                    continue
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                    "link": link,
                    "date": item.get("date", ""),
                })
                if len(results) >= num_results:
                    break
        except Exception:
            pass

        # اگر نتیجه‌ی خبری کافی نبود، جستجوی عمومی وب را هم اضافه کن
        if len(results) < 3:
            for item in ddgs.text(query, max_results=num_results * 2, region="ir-fa"):
                link = item.get("href", "")
                if is_blocked(link):
                    continue
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", ""),
                    "link": link,
                    "date": "",
                })
                if len(results) >= num_results:
                    break
    return results


def build_context(results):
    """تبدیل نتایج جستجو به یک متن قابل استفاده برای پرامپت"""
    context = ""
    for i, r in enumerate(results, start=1):
        context += f"[{i}] عنوان: {r['title']}\n"
        if r.get("date"):
            context += f"    تاریخ: {r['date']}\n"
        context += f"    خلاصه: {r['snippet']}\n"
        context += f"    لینک: {r['link']}\n\n"
    return context


def has_latin_words(text: str) -> bool:
    """بررسی می‌کند که آیا متن شامل کلمات انگلیسی/لاتین ناخواسته است"""
    return bool(re.search(r"[a-zA-Z]{2,}", text))


def ask_openai(question: str, context: str) -> str:
    from openai import OpenAI

    # اینجا کد هوشمند شده: کلید گروک (gsk_...) رو برمی‌داره و به سرور رایگان گروک وصل میشه
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    system_prompt = get_persona_prompt()

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    else:
        user_prompt = f"سؤال کاربر: {question}\n\n(این یک گفتگوی معمولی است، نیازی به جستجو نیست، طبیعی جواب بده.)"

    def _call(extra_reminder: str = "") -> str:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.4,
            max_tokens=700,
            messages=[
                {"role": "system", "content": system_prompt + extra_reminder},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    answer = _call()
    # اگر کلمه‌ی انگلیسی ناخواسته (بیشتر از حد مجاز برای لینک/منبع) در پاسخ بود، یک بار دیگر با یادآوری سخت‌گیرانه امتحان کن
    if has_latin_words(answer) and not context:
        answer = _call("\n\nیادآوری فوری: پاسخ قبلی‌ات کلمه‌ی غیرفارسی داشت. این‌بار کاملاً و فقط با الفبای فارسی بنویس.")
    return answer


def ask_anthropic(question: str, context: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = get_persona_prompt()

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    else:
        user_prompt = f"سؤال کاربر: {question}\n\n(این یک گفتگوی معمولی است، نیازی به جستجو نیست، طبیعی جواب بده.)"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def ask_ollama(question: str, context: str) -> str:
    """استفاده از مدل رایگان و محلی از طریق Ollama (بدون نیاز به کلید API یا پرداخت)"""
    system_prompt = get_persona_prompt()

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    else:
        user_prompt = f"سؤال کاربر: {question}\n\n(این یک گفتگوی معمولی است، نیازی به جستجو نیست، طبیعی جواب بده.)"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["message"]["content"]


def show_in_browser(question: str, answer: str):
    """نمایش جواب در یک صفحه HTML ساده در مرورگر (چون ترمینال ویندوز فارسی را درست نشان نمی‌دهد)"""
    html = f"""
    <html dir="rtl" lang="fa">
    <head>
        <meta charset="UTF-8">
        <title>پاسخ چت‌بات خبری</title>
        <style>
            body {{
                font-family: Tahoma, 'Segoe UI', sans-serif;
                background: #1e1e2f;
                color: #eee;
                padding: 40px;
                max-width: 800px;
                margin: auto;
                line-height: 1.9;
            }}
            h2 {{ color: #7dd3fc; }}
            .question {{ color: #fbbf24; margin-bottom: 20px; }}
            .answer {{ white-space: pre-wrap; background: #2a2a3d; padding: 20px; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <h2>❓ سؤال:</h2>
        <p class="question">{question}</p>
        <h2>✅ پاسخ:</h2>
        <div class="answer">{answer}</div>
    </body>
    </html>
    """
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    webbrowser.open(f"file://{path}")


def answer_question(question: str) -> str:
    context = ""
    if needs_search(question):
        print("\n📰 در حال جستجوی اخبار...")
        results = google_search(question)
        if results:
            context = build_context(results)
    else:
        print("\n💬 گفتگوی معمولی تشخیص داده شد...")

    print("🤖 در حال تولید پاسخ با هوش مصنوعی...")
    if LLM_PROVIDER == "anthropic":
        return ask_anthropic(question, context)
    elif LLM_PROVIDER == "openai":
        return ask_openai(question, context)
    else:
        return ask_ollama(question, context)


def main():
    print("=" * 50)
    print("چت‌بات هوش مصنوعی متصل به گوگل")
    print("برای خروج بنویسید: exit")
    print("=" * 50)

    # مدیریت خطای هوشمند: اگر متغیر خالی بود برنامه کرش نکند و ارور قشنگ بدهد
    missing = []
    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")

    if missing:
        print("\n❌ خطا: این مقادیر در فایل .env تنظیم نشده‌اند:")
        for m in missing:
            print(f"   - {m}")
        print("لطفاً فایل .env را چک کرده و کلید جدید خود را وارد کنید.\n")
        sys.exit(1)

    # دریافت نام کاربر در ابتدای برنامه
    user_name = input("\n👋 اسم شما چیه؟ ").strip()
    if not user_name:
        user_name = "دوست عزیز"

    print(f"\nخوش اومدی {user_name}! 🎉")

    while True:
        question = input(f"\n❓ من آماده‌ام {user_name}: ").strip()
        if question.lower() in ("exit", "quit", "خروج"):
            print(f"\nخداحافظ {user_name} 👋 (ساخته شده توسط تیم فنی persian_ai)")
            break
        if not question:
            continue

        try:
            answer = answer_question(question)
            print("\n✅ پاسخ آماده شد! در حال باز کردن در مرورگر...\n")
            show_in_browser(question, answer)
        except Exception as e:
            print(f"\n⚠️ خطا رخ داد: {e}")


if __name__ == "__main__":
    main()