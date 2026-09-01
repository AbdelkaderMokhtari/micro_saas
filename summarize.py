"""
summarize.py
------------
مسؤول عن استدعاء Gemini API (عبر الـ SDK الجديد google-genai)
وتحويل نص الورقة المستخرج إلى ملخص منظم بخمسة أقسام.

ملاحظة مهمة: Google يغيّر أسماء موديلاتهم بشكل متكرر (تقاعد نماذج
قديمة، إصدار نماذج جديدة كل بضعة أسابيع). قبل ما تشغّل هذا الملف،
تأكد من MODEL_NAME بالأسفل عن طريق مراجعة:
https://ai.google.dev/gemini-api/docs/pricing
واختر موديل مكتوب عليه صراحة "Free" بالعمود الخاص بالـ tier.
"""

import os
import json
from google import genai
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        "ما لقيت GEMINI_API_KEY. تأكد إنك سويت ملف .env "
        "وحطيت فيه: GEMINI_API_KEY=مفتاحك"
    )

client = genai.Client(api_key=API_KEY)

# ⚠️ عدّل هذا الاسم لو تغيّر الموديل المجاني الحالي.
# تحقق من الاسم الصحيح هنا: https://ai.google.dev/gemini-api/docs/pricing
MODEL_NAME = "gemini-3.5-flash-lite"


@dataclass
class PaperSummary:
    tldr: str
    key_contributions: list[str]
    methodology: str
    key_results: list[str]
    limitations: str


SUMMARY_PROMPT_TEMPLATE = """أنت مساعد أكاديمي متخصص بتحليل الأوراق البحثية في مجال
الحوسبة والذكاء الاصطناعي. سأعطيك نص مستخرج من ورقة بحثية (قد يكون مقتطعاً من
أجزاء مختلفة من الورقة: البداية والمنتصف والنهاية).

مهمتك: اقرأ النص وأرجع ملخصاً منظماً بصيغة JSON فقط، بدون أي نص إضافي قبله
أو بعده، وبدون Markdown code fences. الصيغة المطلوبة بالضبط:

{{
  "tldr": "3-4 جمل تشرح المشكلة والحل المقترح بلغة بسيطة",
  "key_contributions": ["مساهمة 1", "مساهمة 2", "..."],
  "methodology": "فقرة قصيرة (3-5 جمل) تشرح المنهجية والـ setup التجريبي",
  "key_results": ["نتيجة أساسية 1", "نتيجة أساسية 2", "..."],
  "limitations": "فقرة قصيرة عن القيود المذكورة بالورقة (أو 'لم تُذكر قيود صريحة بالنص المتاح' إذا ما لقيت شي)"
}}

قواعد مهمة:
- key_contributions و key_results لازم تكون قوائم من 3 إلى 5 نقاط كحد أقصى
- كل نقطة تكون جملة واحدة واضحة ومحددة، مو عامة
- لا تخترع معلومات غير موجودة بالنص - لو معلومة ناقصة، اذكر ذلك صراحة
- اكتب الملخص باللغة العربية بأسلوب أكاديمي واضح، حتى لو النص الأصلي بالإنجليزية

--- نص الورقة ---
{paper_text}
--- نهاية نص الورقة ---

أرجع الآن الـ JSON فقط:"""


def _parse_model_response(raw_text: str) -> dict:
    """يشيل تغليف ```json لو الموديل حطه رغم طلبنا JSON خام."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])
    return json.loads(cleaned)


def summarize_paper(paper_text: str) -> PaperSummary:
    """
    يرسل نص الورقة لـ Gemini ويرجع PaperSummary منظم.

    Raises:
        ValueError: لو الموديل رجع رد ما نقدر نحوله لـ JSON صالح
    """
    prompt = SUMMARY_PROMPT_TEMPLATE.format(paper_text=paper_text)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    try:
        data = _parse_model_response(response.text)
    except (json.JSONDecodeError, AttributeError) as e:
        raise ValueError(
            f"ما قدرت أحلل رد الموديل كـ JSON صالح. "
            f"الرد الخام كان:\n{response.text[:500]}"
        ) from e

    return PaperSummary(
        tldr=data.get("tldr", ""),
        key_contributions=data.get("key_contributions", []),
        methodology=data.get("methodology", ""),
        key_results=data.get("key_results", []),
        limitations=data.get("limitations", ""),
    )


if __name__ == "__main__":
    import sys
    from extract import extract_paper

    if len(sys.argv) < 2:
        print("الاستخدام: python summarize.py path/to/paper.pdf")
        sys.exit(1)

    print("جاري استخراج النص من الملف...")
    extracted = extract_paper(sys.argv[1])
    print(f"تم استخراج {len(extracted.full_text)} حرف. جاري إرسالها لـ Gemini...")

    summary = summarize_paper(extracted.full_text)

    print("\n" + "=" * 50)
    print("TL;DR:")
    print(summary.tldr)

    print("\nالمساهمات الأساسية:")
    for c in summary.key_contributions:
        print(f"  - {c}")

    print("\nالمنهجية:")
    print(summary.methodology)

    print("\nالنتائج الأساسية:")
    for r in summary.key_results:
        print(f"  - {r}")

    print("\nالقيود:")
    print(summary.limitations)