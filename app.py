"""
app.py
------
واجهة Streamlit الرئيسية لأداة Paper Summarizer.
يرفع المستخدم PDF، نستخرج النص، نرسله لـ Gemini، نعرض النتيجة.

يحتفظ بسجل الملخصات خلال الجلسة الواحدة (st.session_state) عشان
المستخدم يقدر يرجع لملخصات سابقة بدون إعادة معالجتها من الصفر.
ملاحظة: هذا السجل يُمسح لو أعدت تحميل الصفحة (F5) أو سكّرت التبويب -
هذا سلوك طبيعي لـ session_state، وكافي لـ MVP (تخزين دائم يحتاج
قاعدة بيانات، نضيفها لاحقاً لو احتجناها).
"""

import streamlit as st
import tempfile
import os

from extract import extract_paper
from summarize import summarize_paper, PaperSummary

st.set_page_config(
    page_title="Paper Summarizer",
    page_icon="📄",
    layout="centered",
)

# نهيّئ السجل مرة وحدة بس، أول ما تبدأ الجلسة
if "history" not in st.session_state:
    st.session_state.history = []  # كل عنصر: dict فيه title, num_pages, summary

# نتتبع أي ملخص من السجل معروض حالياً بالشاشة الرئيسية.
# None يعني: اعرض نتيجة آخر عملية تلخيص جديدة (السلوك الافتراضي)
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None


def render_summary(title: str, num_pages: int, summary: PaperSummary):
    """يعرض ملخص واحد بشكل منظم - نستخدمها لعرض نتيجة جديدة أو عنصر من السجل."""
    st.info(f"📖 **{title}** — {num_pages} صفحة")

    st.subheader("🔑 الخلاصة السريعة (TL;DR)")
    st.write(summary.tldr)

    st.subheader("💡 المساهمات الأساسية")
    for c in summary.key_contributions:
        st.markdown(f"- {c}")

    st.subheader("🧪 المنهجية")
    st.write(summary.methodology)

    st.subheader("📊 النتائج الأساسية")
    for r in summary.key_results:
        st.markdown(f"- {r}")

    st.subheader("⚠️ القيود")
    st.write(summary.limitations)

    markdown_output = f"""# ملخص: {title}

## TL;DR
{summary.tldr}

## المساهمات الأساسية
{chr(10).join(f"- {c}" for c in summary.key_contributions)}

## المنهجية
{summary.methodology}

## النتائج الأساسية
{chr(10).join(f"- {r}" for r in summary.key_results)}

## القيود
{summary.limitations}
"""
    st.download_button(
        label="⬇️ تحميل الملخص كملف Markdown",
        data=markdown_output,
        file_name="summary.md",
        mime="text/markdown",
        key=f"download_{title}_{num_pages}",  # مفتاح فريد يمنع تعارض الأزرار
    )


# ---------- الشريط الجانبي: سجل الملخصات ----------
with st.sidebar:
    st.header("📚 سجل هذه الجلسة")

    if not st.session_state.history:
        st.caption("لسا ما لخصت أي ورقة بهذي الجلسة.")
    else:
        for i, item in enumerate(st.session_state.history):
            # كل ورقة سابقة تظهر كزر - الضغط عليه يعرضها بدون إعادة معالجة
            label = f"{item['title'][:40]}{'...' if len(item['title']) > 40 else ''}"
            if st.button(label, key=f"history_{i}", use_container_width=True):
                st.session_state.selected_index = i

        if st.button("🗑️ مسح السجل", use_container_width=True):
            st.session_state.history = []
            st.session_state.selected_index = None
            st.rerun()


# ---------- المحتوى الرئيسي ----------
st.title("📄 ملخّص الأبحاث العلمية")
st.caption("ارفع ورقة بحثية (PDF) واحصل على ملخص منظم خلال ثوانٍ")

uploaded_file = st.file_uploader(
    "اختر ملف PDF",
    type=["pdf"],
    help="حد أقصى تقريبي: أوراق حتى 20-25 صفحة",
)

if uploaded_file is not None:
    if st.button("لخّص الورقة", type="primary"):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            with st.spinner("جاري استخراج النص من الملف..."):
                extracted = extract_paper(tmp_path)

            with st.spinner("جاري التلخيص عبر الذكاء الاصطناعي..."):
                summary = summarize_paper(extracted.full_text)

            # نضيف النتيجة الجديدة لسجل الجلسة، ونخليها هي المعروضة الآن
            st.session_state.history.append({
                "title": extracted.title_guess,
                "num_pages": extracted.num_pages,
                "summary": summary,
            })
            st.session_state.selected_index = len(st.session_state.history) - 1

            st.success("تم التلخيص بنجاح ✅")

        except Exception as e:
            st.error(f"صار خطأ أثناء المعالجة: {e}")

        finally:
            os.unlink(tmp_path)


# ---------- عرض النتيجة المختارة (إما جديدة أو من السجل) ----------
if st.session_state.selected_index is not None and st.session_state.history:
    idx = st.session_state.selected_index
    # حماية بسيطة لو تغيّر السجل (مثلاً بعد مسح) وصار الـ index غير صالح
    if 0 <= idx < len(st.session_state.history):
        item = st.session_state.history[idx]
        st.divider()
        render_summary(item["title"], item["num_pages"], item["summary"])

st.divider()
st.caption("MVP v0.1 — Paper Summarizer 🚀")