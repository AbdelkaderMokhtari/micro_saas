"""
analytics.py
------------
حقن كود Google Analytics (GA4) داخل ملف index.html بتاع Streamlit،
بلا ما نستخدمو BeautifulSoup - كي فش، غير str.replace() نصي عادي.

الفكرة:
- Streamlit ما يعطيكش وصول مباشر لـ <head> بتاع الصفحة.
- الحل المعروف: نلقاو ملف index.html اللي جوه مكتبة streamlit المثبتة،
  ونزيدو فيه سكريبت GA قبل </head> مباشرة.
- نتأكدو ما نزيدوهش مرتين (idempotent) باش ما يتكررش الحقن كل مرة يعاود
  يشتغل التطبيق أو يعاود يتحمّل.
"""

import os
import streamlit as st

# حط هنا Measurement ID تاعك (نفس اللي بان في Google Analytics)
GA_MEASUREMENT_ID = "G-HV8L9G0D43"

GA_SNIPPET = f"""
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>
"""


def inject_ga() -> None:
    """
    يحقن كود GA مرة وحدة فقط بملف index.html بتاع streamlit.
    ما كاين حتى استعمال لـ BeautifulSoup - غير قراءة/كتابة نص عادية.
    """
    try:
        index_path = os.path.join(
            os.path.dirname(st.__file__), "static", "index.html"
        )

        if not os.path.exists(index_path):
            # ما نطيّحوش التطبيق إذا المسار تبدّل بنسخة جديدة من streamlit
            return

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # إذا كود GA موجود من قبل، ما نزيدوهش مرة أخرى
        if GA_MEASUREMENT_ID in html:
            return

        if "</head>" in html:
            html = html.replace("</head>", GA_SNIPPET + "</head>", 1)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(html)

    except Exception:
        # أي خطأ هنا ما لازمش يوقف التطبيق - GA مو أساسي لعمل الأداة
        pass