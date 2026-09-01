"""
extract.py
----------
مسؤول عن استخراج النص من ملف PDF بطريقة تقلل حجم الـ input
اللي نرسله لاحقاً لـ LLM، مع الحفاظ على المعلومات المهمة.

الاستراتيجية:
- لو الورقة قصيرة (<= 12 صفحة): نرسل كل النص، ما فيه داعي نعقّد
- لو طويلة: نرسل أول 3 صفحات كاملة (Abstract + Intro) + آخر صفحتين
  (Conclusion) + عيّنة من المنتصف، بدل الورقة كاملة
"""

import pymupdf  # PyMuPDF (الاسم القديم للاستيراد كان fitz، الجديد pymupdf)
from dataclasses import dataclass


@dataclass
class ExtractedPaper:
    full_text: str
    num_pages: int
    title_guess: str  # أفضل تخمين لعنوان الورقة (أول سطر كبير بالصفحة الأولى)


def _guess_title(first_page_text: str) -> str:
    """
    تخمين بسيط لعنوان الورقة: نأخذ أول سطر غير فارغ وطوله معقول.
    مو دقيق 100%، لكن كافي لعرضه بالواجهة كمرجع للمستخدم.
    """
    lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
    for line in lines[:5]:
        # نتجاهل أسطر قصيرة جداً (غالباً أرقام صفحات أو رموز)
        if len(line) > 15:
            return line
    return "عنوان غير معروف"


def extract_paper(pdf_path: str, max_full_pages: int = 12) -> ExtractedPaper:
    """
    يفتح ملف PDF ويستخرج نصه بذكاء حسب طوله.

    Args:
        pdf_path: مسار ملف الـ PDF على القرص
        max_full_pages: لو عدد صفحات الورقة أقل من أو يساوي هذا الرقم،
                         نرسل النص كامل بدون اقتطاع

    Returns:
        ExtractedPaper يحتوي النص المستخرج + معلومات إضافية
    """
    doc = pymupdf.open(pdf_path)
    num_pages = len(doc)

    if num_pages == 0:
        raise ValueError("الملف فارغ أو لا يمكن قراءته")

    first_page_text = doc[0].get_text()
    title_guess = _guess_title(first_page_text)

    if num_pages <= max_full_pages:
        # ورقة قصيرة: خذ كل شي، ما فيه داعي نقتطع
        full_text = "\n\n".join(page.get_text() for page in doc)
    else:
        # ورقة طويلة: بدل ما ناخذ عيّنة وحدة صغيرة من المنتصف (كانت تفوّت
        # محتوى كبير بالأوراق الطويلة جداً، مثل محاضرات 25+ صفحة)، نوزّع
        # العيّنة على عدة نقاط: ربع، نص، وثلاث أرباع الورقة. هذا يغطي
        # المحتوى بشكل أعدل بدون ما نرسل الورقة كاملة.
        intro_pages = doc[:3]
        conclusion_pages = doc[-2:]

        # نحدد 3 نقاط توزيع بالجزء الأوسط من الورقة (نستثني أول/آخر 3 صفحات
        # لأنها مغطاة أصلاً بـ intro/conclusion)
        usable_start = 3
        usable_end = num_pages - 2
        span = usable_end - usable_start

        checkpoints = [
            usable_start + span // 4,       # ربع الورقة
            usable_start + span // 2,       # نص الورقة
            usable_start + (3 * span) // 4,  # ثلاث أرباع الورقة
        ]

        # كل نقطة تاخذ صفحة وحدة، مع تجنب التكرار لو الورقة قصيرة نسبياً
        middle_page_indices = sorted(set(
            p for p in checkpoints if usable_start <= p < usable_end
        ))
        middle_pages = [doc[i] for i in middle_page_indices]

        parts = []
        parts.append("=== بداية الورقة (Abstract / Introduction) ===")
        parts.extend(p.get_text() for p in intro_pages)

        parts.append(
            "\n=== عيّنات موزّعة من أجزاء مختلفة بمنتصف الورقة "
            "(Methodology/Results/أقسام إضافية) ==="
        )
        for i, p in zip(middle_page_indices, middle_pages):
            parts.append(f"--- (صفحة رقم {i + 1} تقريباً) ---")
            parts.append(p.get_text())

        parts.append("\n=== نهاية الورقة (Conclusion) ===")
        parts.extend(p.get_text() for p in conclusion_pages)

        full_text = "\n\n".join(parts)

    doc.close()

    return ExtractedPaper(
        full_text=full_text,
        num_pages=num_pages,
        title_guess=title_guess,
    )


if __name__ == "__main__":
    # اختبار سريع - شغّل هذا الملف مباشرة مع مسار PDF لتجربته
    import sys

    if len(sys.argv) < 2:
        print("الاستخدام: python extract.py path/to/paper.pdf")
        sys.exit(1)

    result = extract_paper(sys.argv[1])
    print(f"عدد الصفحات: {result.num_pages}")
    print(f"العنوان المخمّن: {result.title_guess}")
    print(f"طول النص المستخرج: {len(result.full_text)} حرف")
    print("---")
    print(result.full_text[:500], "...")