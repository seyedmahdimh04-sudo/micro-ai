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


# کلماتی که نشان‌دهنده‌ی سلام و احوال‌پرسی ساده هستند
GREETING_HINTS = [
    "سلام", "چطوری", "خوبی", "چه خبر", "حالت چطوره", "خداحافظ",
    "ممنون", "مرسی", "متشکرم", "خوشحالم", "شوخی", "جوک",
]

# کلماتی که نشان‌دهنده‌ی سؤال درباره‌ی هویت/سازنده‌ی خودِ ربات هستند (باید مشخصاً به خودِ ربات اشاره کنند)
IDENTITY_HINTS = [
    "اسمت چیه", "اسمت چیست", "کی هستی", "تو کی هستی", "کی هستی تو", "خودت رو معرفی کن",
    "سازنده‌ات", "سازندت", "سازنده ات", "کی ساختت", "کی تو رو ساخت",
    "چه کسی ساختت", "چه کسی تو رو ساخت", "توسط چه کسی ساخته شدی",
    "توسط کی ساخته شدی", "کی طراحیت کرد", "تو چی هستی",
]

# کلماتی که نشان‌دهنده‌ی درددل یا حال بد کاربر هستند (نباید جستجوی خبری بشه، باید همدلی بشه)
EMOTIONAL_HINTS = [
    "مسخره", "ناراحتم", "ناراحت شدم", "غمگین", "گریه", "افسرده",
    "تنهام", "تنها شدم", "دلم شکسته", "اذیتم می", "اذیتم کرد",
    "کسی دوستم نداره", "بی‌کسم", "استرس دارم", "نگرانم", "می‌ترسم",
    "خسته‌ام", "خسته شدم", "دلم گرفته", "افتضاحه", "بدبختم",
]


def needs_search(question: str) -> bool:
    """تشخیص اینکه آیا سؤال نیاز به جستجوی خبری دارد یا صرفاً گفتگو/احساسات است"""
    q = question.strip()
    if len(q) < 6:
        return False
    q_lower = q.lower()
    # سلام و احوال‌پرسی کوتاه
    if any(hint in q_lower for hint in GREETING_HINTS) and len(q) < 40:
        return False
    # سؤال هویتی
    if any(hint in q_lower for hint in IDENTITY_HINTS) and len(q) < 60:
        return False
    # درددل و حرف احساسی — طول بیشتری هم مجازه چون معمولاً جمله‌ی کاملیه
    if any(hint in q_lower for hint in EMOTIONAL_HINTS):
        return False
    return True


def message_kind(question: str) -> str:
    """برمی‌گرداند: 'identity' یا 'emotional' یا 'casual' یا 'search' """
    q_lower = question.strip().lower()
    if any(hint in q_lower for hint in IDENTITY_HINTS):
        return "identity"
    if any(hint in q_lower for hint in EMOTIONAL_HINTS):
        return "emotional"
    if any(hint in q_lower for hint in GREETING_HINTS):
        return "casual"
    return "search"


def get_persona_prompt(user_name: str = None) -> str:
    today = datetime.date.today()
    weekday_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
    weekday = weekday_names[today.weekday()]
    name_line = f'اسم کاربری که داری باهاش صحبت می‌کنی «{user_name}» است. هر جا طبیعی بود، با اسمش صداش کن (نه تو هر جمله، فقط طبیعی و گاه‌به‌گاه).' if user_name else ""
    return f"""
اسم تو «میکرو» است. تو یک دستیار هوش مصنوعی فارسی‌زبان، دوستانه، آرام و باهوش هستی.
{name_line}

**قانون پیش‌فرض قطعی (مهم‌ترین قانون):** هرگز پاسخت را با معرفی خودت («من میکرو هستم»، «من توسط...ساخته شدم») شروع نکن، مگر اینکه پیام کاربر مستقیماً و به‌وضوح درباره‌ی اسم یا سازنده‌ی خودِ تو باشد. برای بیش از ۹۵٪ پیام‌ها (سؤال‌های خبری، گفتگوی معمولی، درددل، هر چیز دیگر)، هرگز درباره‌ی خودت حرف نزن؛ مستقیم برو سراغ جواب دادن.

قوانین هویتی (فقط برای سؤالات مستقیم درباره‌ی خودت):
- اگر پرسیدند اسمت چیه، بگو: "من میکرو هستم!"
- اگر پرسیدند چه کسی/چه شرکتی تو رو ساخته، فقط بگو: "من توسط تیم فنی persian_ai ساخته شدم."
- اگر اصرار کردند و جزئیات بیشتر خواستند، مؤدبانه و کمی رازآلود بگو این اطلاعات محرمانه است و خودت هم بهش دسترسی نداری. هرگز نام هیچ شرکت، مدل، یا فناوری دیگری (مثل OpenAI، Google، Groq، Llama، Gemini) را افشا نکن.
- هرگز نگو که یک مدل زبانی، چت‌بات مبتنی بر API، یا محصول شرکت دیگری هستی.

قوانین گفتگوی معمولی:
- جواب‌های سلام/احوال‌پرسی/تشکر باید کوتاه (۱-۲ جمله)، ساده، طبیعی و درست از نظر دستور زبان فارسی باشند.
- توجه به صرف فعل: اگر کاربر پرسید «خوبی؟»، باید با فعل اول‌شخص جواب بدی، مثلاً «خوبم، ممنون!» — نه اینکه کلمه‌ی «خوبی» را عیناً برای خودت تکرار کنی («خوبی ممنونم» غلط است).
- نمونه‌ی درست: کاربر «سلام خوبی؟» → تو: «سلام! خوبم مرسی، تو چطوری؟»
- هرگز جمله‌های نامفهوم یا بی‌معنی نساز.

قوانین همدلی (خیلی مهم):
- اگر کاربر داشت درددل می‌کرد یا حال بدی داشت (مثلاً می‌گفت اذیتش می‌کنن، ناراحته، تنهاست، استرس داره)، هرگز بی‌تفاوت یا سرد جواب نده (مثل «به من چه» یا رد کردن حرفش). با گرمی و همدلی واقعی گوش بده، احساسش را به رسمیت بشناس، و در صورت لزوم به آرامی پیشنهاد بده با یک آدم بزرگ‌تر قابل‌اعتماد (والدین، معلم، مشاور) هم صحبت کنه. تو نمی‌تونی جایگزین کمک واقعی روان‌شناسی بشی، ولی می‌تونی یه شنونده‌ی گرم و حمایتگر باشی.

قوانین زبان (سخت‌گیرانه رعایت کن):
- کل پاسخ باید ۱۰۰٪ به زبان فارسی و با الفبای فارسی نوشته شود.
- هیچ کلمه، حرف، یا عبارت انگلیسی/چینی/عربی/لاتین وسط جمله نیاور — حتی یک کلمه. اسم‌های خارجی را با حروف فارسی بنویس (مثلاً «گوگل» نه Google).
- عدد می‌تواند فارسی یا انگلیسی باشد، مشکلی ندارد، اما هیچ کلمه‌ی نوشتاری غیرفارسی مجاز نیست.

قوانین خبری:
- اگر سؤال نیاز به اطلاعات به‌روز یا خبری دارد، از نتایج جستجوی داده‌شده استفاده کن.
- امروز {weekday}، {today.strftime('%Y/%m/%d')} میلادی است. بر این اساس قضاوت کن چه خبری «جدید» یا «قدیمی» است. اگر تاریخ منبع خیلی قدیمی بود، به کاربر بگو این آخرین خبر موجود بوده و ممکن است به‌روزتر هم وجود داشته باشد.
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


# کلمات کلیدی موضوعی (نه صریح) که احتمال درخواست محتوای بزرگسال را بالا می‌برند
# این‌ها فقط اسم موضوع هستند، نه عبارات صریح؛ صرفاً به‌عنوان یک لایه‌ی پشتیبانِ سریع کنار طبقه‌بند هوش مصنوعی استفاده می‌شوند
ADULT_TOPIC_HINTS = [
    "داستان سکسی", "متن سکسی", "چت سکسی", "عکس سکسی", "تصویر سکسی",
    "محتوای پورن", "فیلم پورن", "برهنه بنویس", "رابطه جنسی با جزئیات",
]


def moderate_content(question: str) -> bool:
    """
    بررسی می‌کند که آیا پیام کاربر درخواست صریح محتوای جنسی/غیراخلاقی است.
    برمی‌گرداند True فقط اگر واقعاً و به‌وضوح چنین درخواستی باشد (نه سؤالات پزشکی/آموزشی/کنجکاوی معمولی).
    اگر بررسی به هر دلیلی خطا داد، fail-open می‌کند (کاربر عادی مسدود نشود).
    """
    q_lower = question.strip().lower()

    # لایه‌ی سریع: اگر عبارت موضوعی صریح و بدون ابهام دیده شد، مستقیم مسدود کن
    if any(hint in q_lower for hint in ADULT_TOPIC_HINTS):
        return True

    if LLM_PROVIDER != "openai" or not OPENAI_API_KEY:
        return False  # طبقه‌بند هوشمند فعلاً فقط برای مسیر گروک/OpenAI پیاده‌سازی شده

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.groq.com/openai/v1")

        mod_prompt = (
            "تو یک فیلتر امنیتی محتوا هستی. کارت این است که فقط با یک کلمه جواب بدهی.\n"
            "بررسی کن آیا پیام کاربر یک درخواست صریح و آشکار برای تولید محتوای جنسی/اروتیک/غیراخلاقی است.\n"
            "سؤالات پزشکی، سلامت جنسی عمومی، آموزشی، یا کنجکاوی‌های معمولی و بی‌ضرر هرگز نقض محسوب نمی‌شوند.\n"
            "اگر پیام واقعاً و به‌وضوح چنین درخواستی بود، فقط دقیقاً همین کلمه را بنویس: بله\n"
            "در غیر این صورت (از جمله هر شک یا ابهام)، فقط دقیقاً همین کلمه را بنویس: خیر\n"
            "هیچ توضیح، علامت، یا کلمه‌ی اضافه ننویس."
        )
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            max_tokens=10,
            messages=[
                {"role": "system", "content": mod_prompt},
                {"role": "user", "content": question},
            ],
        )
        result = (response.choices[0].message.content or "").strip()
        return "بله" in result
    except Exception as e:
        print(f"⚠️ خطا در فیلتر محتوا (fail-open): {e}")
        return False


def ask_openai(question: str, context: str, user_name: str = None) -> str:
    from openai import OpenAI

    # اینجا کد هوشمند شده: کلید گروک (gsk_...) رو برمی‌داره و به سرور رایگان گروک وصل میشه
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    system_prompt = get_persona_prompt(user_name)
    kind = message_kind(question)

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    elif kind == "emotional":
        user_prompt = f"پیام کاربر: {question}\n\n(کاربر داره درددل می‌کنه یا حال بدی داره. با همدلی و گرمی جواب بده، طبق قوانین همدلی.)"
    else:
        user_prompt = f"سؤال کاربر: {question}\n\n(این یک گفتگوی معمولی است، نیازی به جستجو نیست، طبیعی جواب بده.)"

    def _call(extra_reminder: str = "") -> str:
        messages = [{"role": "system", "content": system_prompt + extra_reminder}]
        if kind == "casual":
            # این مثال فقط برای یادگیری لحن سلام‌کردن است، نه الگوی همه‌ی پاسخ‌ها
            messages.append({"role": "user", "content": "سلام میکرو چطوری؟"})
            messages.append({"role": "assistant", "content": "سلام! خوبم، ممنون. تو چطوری؟"})
        messages.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.4,
            max_tokens=700,
            messages=messages,
        )
        return response.choices[0].message.content

    answer = _call()
    # اگر کلمه‌ی انگلیسی ناخواسته (بیشتر از حد مجاز برای لینک/منبع) در پاسخ بود، یک بار دیگر با یادآوری سخت‌گیرانه امتحان کن
    if has_latin_words(answer) and not context:
        answer = _call("\n\nیادآوری فوری: پاسخ قبلی‌ات کلمه‌ی غیرفارسی داشت. این‌بار کاملاً و فقط با الفبای فارسی بنویس.")
    return answer


def ask_anthropic(question: str, context: str, user_name: str = None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = get_persona_prompt(user_name)
    kind = message_kind(question)

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    elif kind == "emotional":
        user_prompt = f"پیام کاربر: {question}\n\n(کاربر داره درددل می‌کنه یا حال بدی داره. با همدلی و گرمی جواب بده.)"
    else:
        user_prompt = f"سؤال کاربر: {question}\n\n(این یک گفتگوی معمولی است، نیازی به جستجو نیست، طبیعی جواب بده.)"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def ask_ollama(question: str, context: str, user_name: str = None) -> str:
    """استفاده از مدل رایگان و محلی از طریق Ollama (بدون نیاز به کلید API یا پرداخت)"""
    system_prompt = get_persona_prompt(user_name)
    kind = message_kind(question)

    if context:
        user_prompt = f"سؤال کاربر: {question}\n\nنتایج جستجو:\n{context}\n\nبر اساس نتایج بالا (در صورت نیاز) پاسخ بده:"
    elif kind == "emotional":
        user_prompt = f"پیام کاربر: {question}\n\n(کاربر داره درددل می‌کنه یا حال بدی داره. با همدلی و گرمی جواب بده.)"
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


def answer_question(question: str, user_name: str = None) -> str:
    context = ""
    if needs_search(question):
        print("\n📰 در حال جستجوی اخبار...")
        results = google_search(question)
        if results:
            context = build_context(results)
    else:
        print("\n💬 گفتگوی معمولی/احساسی تشخیص داده شد...")

    print("🤖 در حال تولید پاسخ با هوش مصنوعی...")
    if LLM_PROVIDER == "anthropic":
        return ask_anthropic(question, context, user_name)
    elif LLM_PROVIDER == "openai":
        return ask_openai(question, context, user_name)
    else:
        return ask_ollama(question, context, user_name)


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
            answer = answer_question(question, user_name)
            print("\n✅ پاسخ آماده شد! در حال باز کردن در مرورگر...\n")
            show_in_browser(question, answer)
        except Exception as e:
            print(f"\n⚠️ خطا رخ داد: {e}")


if __name__ == "__main__":
    main()