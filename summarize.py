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


def _build_prompt(paper_text: str, language: str) -> str:
    """
    يبني الـ prompt حسب لغة الإخراج المطلوبة (ar أو en).
    بنية JSON نفسها بالحالتين - يتغيّر بس لغة التعليمات ولغة المخرجات.
    """
    if language == "en":
        return f"""You are an academic assistant specialized in analyzing research
papers in computer science and AI. I will give you text extracted from a
research paper (it may be a sample from different parts of the paper: the
beginning, middle, and end).

Your task: read the text and return a structured summary in JSON format
ONLY, with no extra text before or after it, and no Markdown code fences.
The exact required format:

{{
  "tldr": "3-4 sentences explaining the problem and the proposed solution in simple language",
  "key_contributions": ["contribution 1", "contribution 2", "..."],
  "methodology": "a short paragraph (3-5 sentences) explaining the methodology and experimental setup",
  "key_results": ["key result 1", "key result 2", "..."],
  "limitations": "a short paragraph about limitations mentioned in the paper (or 'No explicit limitations were mentioned in the available text' if none found)"
}}

Important rules:
- key_contributions and key_results must be lists of 4 to 6 points maximum
- each point should be one clear, specific sentence, not generic
- IMPORTANT: the text sent to you is divided into several parts marked with
  "===" (e.g. beginning of paper, samples from the middle, end of paper).
  Each part usually contains a different idea or concept. Do not just
  summarize one part or repeat the same idea in different phrasing - make
  sure you cover at least one independent point from each major part
  mentioned in the text, even if they are scattered concepts (such as
  evaluation criteria, procedural steps, additional definitions)
- do not invent information that isn't in the text - if information is
  missing, state that explicitly
- write the summary in clear academic English, even if the original text is
  in another language

--- paper text ---
{paper_text}
--- end of paper text ---

Now return the JSON only:"""

    # الافتراضي: عربي
    return f"""أنت مساعد أكاديمي متخصص بتحليل الأوراق البحثية في مجال
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
- key_contributions و key_results لازم تكون قوائم من 4 إلى 6 نقاط كحد أقصى
- كل نقطة تكون جملة واحدة واضحة ومحددة، مو عامة
- ⚠️ مهم جداً: النص المرسل لك مقسّم لعدة أجزاء بعلامات "===" (مثل بداية الورقة،
  عيّنات من المنتصف، نهاية الورقة). كل جزء غالباً يحتوي معلومة أو مفهوم مختلف
  عن باقي الأجزاء. لا تكتفِ بتلخيص جزء واحد أو تكرار نفس الفكرة بصيغ مختلفة -
  تأكد إنك غطّيت على الأقل نقطة واحدة مستقلة من كل جزء رئيسي مذكور بالنص،
  حتى لو كانت مفاهيم متفرقة (مثل: معايير تقييم، خطوات عملية، تعريفات إضافية)
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


def summarize_paper(paper_text: str, language: str = "ar") -> PaperSummary:
    """
    يرسل نص الورقة لـ Gemini ويرجع PaperSummary منظم.

    Args:
        paper_text: النص المستخرج من الورقة
        language: لغة الملخص المطلوب - "ar" (عربي، الافتراضي) أو "en" (إنجليزي)

    Raises:
        ValueError: لو الموديل رجع رد ما نقدر نحوله لـ JSON صالح
    """
    prompt = _build_prompt(paper_text, language)

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