"""
app.py
------
واجهة Streamlit الرئيسية لأداة Paper Summarizer.
يرفع المستخدم PDF، نستخرج النص، نرسله لـ Gemini، نعرض النتيجة.

يدعم لغتين للواجهة والمخرجات: العربية (ar) والإنجليزية (en).
يحتفظ بسجل الملخصات خلال الجلسة الواحدة (st.session_state).

يحتوي أيضاً على حقن كود Google Analytics (GA4) عبر analytics.py
(بلا استخدام BeautifulSoup - راجع analytics.py للتفاصيل).
"""

import streamlit as st
import tempfile
import os

from extract import extract_paper
from summarize import summarize_paper, PaperSummary
from Ga_tracking import inject_ga

st.set_page_config(
    page_title="Paper Summarizer",
    page_icon="🔬",
    layout="centered",
)

# ---------- حقن Google Analytics ----------
# لازم تكون بعد set_page_config مباشرة وقبل أي عرض آخر بالصفحة
inject_ga()

# ---------- نصوص الواجهة بكل لغة ----------
# كل نص بالتطبيق موجود هنا مرتين (ar/en) - نستدعيه عبر دالة T() بالأسفل
TEXTS = {
    "ar": {
        "title": "🔬 ملخّص الأبحاث العلمية",
        "intro": (
            "أداة تساعد الباحثين وطلاب الماجستير/الدكتوراه على فهم الأوراق "
            "العلمية بسرعة — ارفع ملف PDF واحصل على ملخص منظم خلال ثوانٍ "
            "بدل قراءة الورقة كاملة."
        ),
        "how_it_works_title": "ℹ️ كيف تعمل هذي الأداة؟",
        "how_it_works_body": """
1. **ارفع** ملف PDF لورقة بحثية (أو محاضرة/كورس تعليمي)
2. الأداة تستخرج النص وترسله لنموذج ذكاء اصطناعي (Gemini) للتحليل
3. تحصل خلال ثوانٍ على ملخص من خمسة أقسام: الخلاصة السريعة، المساهمات
   الأساسية، المنهجية، النتائج، والقيود
4. تقدر تحمّل الملخص كملف Markdown، أو ترجع له لاحقاً من السجل بالشريط الجانبي

**ملاحظة على الخصوصية:** الملف يُعالج مؤقتاً فقط لإنتاج الملخص ولا يُخزَّن
بشكل دائم على الخادم. مع ذلك، تجنّب رفع أوراق تحتوي معلومات حساسة أو سرّية.

⚠️ الملخصات مُولّدة تلقائياً بالذكاء الاصطناعي وقد تحتوي أخطاء أو تفاصيل
ناقصة — استخدمها كنقطة بداية سريعة، لا كبديل كامل عن قراءة الورقة الأصلية.
""",
        "uploader_label": "اختر ملف PDF",
        "uploader_help": "حد أقصى تقريبي: أوراق حتى 20-25 صفحة",
        "summarize_button": "لخّص الورقة",
        "extracting_spinner": "جاري استخراج النص من الملف...",
        "summarizing_spinner": "جاري التلخيص عبر الذكاء الاصطناعي...",
        "success_msg": "تم التلخيص بنجاح ✅",
        "error_prefix": "صار خطأ أثناء المعالجة:",
        "sidebar_history_title": "📚 سجل هذه الجلسة",
        "sidebar_empty": "لازلت لم تلخص أي ورقة بهذه الجلسة.",
        "clear_history": "🗑️ مسح السجل",
        "pages_label": "عدد الصفحات",
        "tldr_title": "🔑 الخلاصة السريعة (TL;DR)",
        "contributions_title": "💡 المساهمات الأساسية",
        "methodology_title": "🧪 المنهجية",
        "results_title": "📊 النتائج الأساسية",
        "limitations_title": "⚠️ القيود",
        "download_button": "⬇️ تحميل الملخص كملف Markdown",
        "footer": (
            "📄 Paper Summarizer — MVP v0.1 · مشروع شخصي قيد التطوير · "
            "ملاحظاتك مرحّب بها لتحسين الأداة"
        ),
        "md_summary_of": "ملخص",
        "language_selector_label": "🌐 اللغة",
    },
    "en": {
        "title": "🔬 Paper Summarizer",
        "intro": (
            "A tool that helps researchers and graduate students quickly "
            "understand academic papers — upload a PDF and get a structured "
            "summary in seconds instead of reading the whole paper."
        ),
        "how_it_works_title": "ℹ️ How does this tool work?",
        "how_it_works_body": """
1. **Upload** a PDF of a research paper (or a lecture/course slide deck)
2. The tool extracts the text and sends it to an AI model (Gemini) for analysis
3. Within seconds, you get a summary with five sections: TL;DR, key
   contributions, methodology, results, and limitations
4. You can download the summary as a Markdown file, or revisit it later from
   the session history in the sidebar

**Privacy note:** your file is processed temporarily just to generate the
summary and is not permanently stored on the server. Still, avoid uploading
papers with sensitive or confidential information.

⚠️ Summaries are AI-generated and may contain errors or missing details —
use them as a quick starting point, not a full replacement for reading the
original paper.
""",
        "uploader_label": "Choose a PDF file",
        "uploader_help": "Approximate limit: papers up to 20-25 pages",
        "summarize_button": "Summarize Paper",
        "extracting_spinner": "Extracting text from the file...",
        "summarizing_spinner": "Summarizing with AI...",
        "success_msg": "Summary generated successfully ✅",
        "error_prefix": "An error occurred while processing:",
        "sidebar_history_title": "📚 This Session's History",
        "sidebar_empty": "You haven't summarized any paper yet this session.",
        "clear_history": "🗑️ Clear History",
        "pages_label": "Pages",
        "tldr_title": "🔑 TL;DR",
        "contributions_title": "💡 Key Contributions",
        "methodology_title": "🧪 Methodology",
        "results_title": "📊 Key Results",
        "limitations_title": "⚠️ Limitations",
        "download_button": "⬇️ Download Summary as Markdown",
        "footer": (
            "📄 Paper Summarizer — MVP v0.1 · a personal project in progress · "
            "feedback is welcome to improve the tool"
        ),
        "md_summary_of": "Summary",
        "language_selector_label": "🌐 Language",
    },
}


def T(key: str) -> str:
    """يرجع النص المطابق للغة المختارة حالياً بالجلسة."""
    return TEXTS[st.session_state.language][key]


# ---------- تهيئة حالة الجلسة ----------
if "language" not in st.session_state:
    st.session_state.language = "ar"  # الافتراضي عربي

if "history" not in st.session_state:
    st.session_state.history = []  # كل عنصر: dict فيه title, num_pages, summary, language

if "selected_index" not in st.session_state:
    st.session_state.selected_index = None


# ---------- زر تبديل اللغة (أعلى الصفحة) ----------
lang_col1, lang_col2 = st.columns([4, 1])
with lang_col2:
    selected = st.selectbox(
        T("language_selector_label"),
        options=["ar", "en"],
        format_func=lambda x: "العربية" if x == "ar" else "English",
        index=0 if st.session_state.language == "ar" else 1,
        label_visibility="collapsed",
    )
    if selected != st.session_state.language:
        st.session_state.language = selected
        st.rerun()

# ---------- اتجاه الصفحة حسب اللغة (RTL للعربي، LTR للإنجليزي) ----------
direction = "rtl" if st.session_state.language == "ar" else "ltr"
text_align = "right" if st.session_state.language == "ar" else "left"
st.markdown(
    f"""
    <style>
    .block-container {{ direction: {direction}; text-align: {text_align}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def render_summary(title: str, num_pages: int, summary: PaperSummary):
    """يعرض ملخص واحد بشكل منظم - نستخدمها لعرض نتيجة جديدة أو عنصر من السجل."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 📖 {title}")
    with col2:
        st.metric(T("pages_label"), num_pages)

    st.subheader(T("tldr_title"))
    st.write(summary.tldr)

    st.subheader(T("contributions_title"))
    for c in summary.key_contributions:
        st.markdown(f"- {c}")

    st.subheader(T("methodology_title"))
    st.write(summary.methodology)

    st.subheader(T("results_title"))
    for r in summary.key_results:
        st.markdown(f"- {r}")

    st.subheader(T("limitations_title"))
    st.write(summary.limitations)

    markdown_output = f"""# {T('md_summary_of')}: {title}

## TL;DR
{summary.tldr}

## {T('contributions_title')}
{chr(10).join(f"- {c}" for c in summary.key_contributions)}

## {T('methodology_title')}
{summary.methodology}

## {T('results_title')}
{chr(10).join(f"- {r}" for r in summary.key_results)}

## {T('limitations_title')}
{summary.limitations}
"""
    st.download_button(
        label=T("download_button"),
        data=markdown_output,
        file_name="summary.md",
        mime="text/markdown",
        key=f"download_{title}_{num_pages}",
    )


# ---------- الشريط الجانبي: سجل الملخصات ----------
with st.sidebar:
    st.header(T("sidebar_history_title"))

    if not st.session_state.history:
        st.caption(T("sidebar_empty"))
    else:
        for i, item in enumerate(st.session_state.history):
            label = f"{item['title'][:40]}{'...' if len(item['title']) > 40 else ''}"
            if st.button(label, key=f"history_{i}", use_container_width=True):
                st.session_state.selected_index = i

        if st.button(T("clear_history"), use_container_width=True):
            st.session_state.history = []
            st.session_state.selected_index = None
            st.rerun()


# ---------- المحتوى الرئيسي ----------
st.title(T("title"))
st.markdown(T("intro"))

with st.expander(T("how_it_works_title")):
    st.markdown(T("how_it_works_body"))

st.divider()

uploaded_file = st.file_uploader(
    T("uploader_label"),
    type=["pdf"],
    help=T("uploader_help"),
)

if uploaded_file is not None:
    if st.button(T("summarize_button"), type="primary"):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            with st.spinner(T("extracting_spinner")):
                extracted = extract_paper(tmp_path)

            with st.spinner(T("summarizing_spinner")):
                summary = summarize_paper(
                    extracted.full_text,
                    language=st.session_state.language,
                )

            # نخزن لغة الملخص وقت إنشائه - عشان لو رجع المستخدم يشوفه من
            # السجل بعد ما بدّل اللغة، يبان بنفس اللغة اللي انولّد فيها
            st.session_state.history.append({
                "title": extracted.title_guess,
                "num_pages": extracted.num_pages,
                "summary": summary,
                "language": st.session_state.language,
            })
            st.session_state.selected_index = len(st.session_state.history) - 1

            st.success(T("success_msg"))

        except Exception as e:
            st.error(f"{T('error_prefix')} {e}")

        finally:
            os.unlink(tmp_path)


# ---------- عرض النتيجة المختارة (إما جديدة أو من السجل) ----------
if st.session_state.selected_index is not None and st.session_state.history:
    idx = st.session_state.selected_index
    if 0 <= idx < len(st.session_state.history):
        item = st.session_state.history[idx]
        st.divider()
        render_summary(item["title"], item["num_pages"], item["summary"])

st.divider()
st.caption(T("footer"))