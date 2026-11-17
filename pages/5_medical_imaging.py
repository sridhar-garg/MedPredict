"""Research-only imaging and document analysis integrated with MedPredict."""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from medical_addon_core import (
    assess_egfr, assess_haemoglobin, assess_ldl, egfr_2021, extract_candidate_lab_values,
)
from imaging_models import MODALITIES, lookup_model, infer
from utils import apply_custom_css

st.set_page_config(page_title="Medical Imaging & Reports | MedPredict", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")


from sidebar_compat import show_sidebar
show_sidebar()
apply_custom_css()

if not st.session_state.get("is_logged_in", False):
    st.warning("Please sign in on the MedPredict dashboard before opening this page.")
    if st.button("Open login / dashboard"):
        st.switch_page("app.py")
    st.stop()

st.title("🔬 Medical Imaging & Report Explorer")
st.info(
    "**Research / education only — not medical diagnosis.** The uploaded image might be outside a model's training distribution. "
    "Scores are uncalibrated model outputs, not disease probabilities. Results cannot confirm or rule out an illness. "
    "Use synthetic or appropriately de-identified test samples only."
)

modality = st.selectbox("1. What are you uploading?", list(MODALITIES), key="mp_modality")
part = st.selectbox("2. Which body part?", MODALITIES[modality], key="mp_part") if MODALITIES[modality] else None
is_report = modality == "Health checkup report"
uploaded = st.file_uploader(
    "3. Select the scan image or report",
    type=["pdf", "png", "jpg", "jpeg"] if is_report else ["png", "jpg", "jpeg"],
    help="Maximum 12 MB. Radiology image classifiers take a single image, not full CT/MRI studies.",
)


def load_image(data: bytes):
    try:
        image = Image.open(BytesIO(data))
        image = ImageOps.exif_transpose(image)
        if image.width * image.height > 20_000_000:
            st.error("Image too large. Please use an image under 20 megapixels.")
            st.stop()
        image.load()
        return image
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        st.error(f"Could not decode this image: {type(exc).__name__}.")
        st.stop()


def extract_report_text(data: bytes, filename: str) -> tuple[str, str]:
    """Extract PDF text; use local Tesseract OCR on scans when installed."""
    suffix = filename.lower().split(".")[-1]
    if suffix == "pdf":
        from pypdf import PdfReader
        doc = PdfReader(BytesIO(data))
        if len(doc.pages) > 15:
            return "", "Please upload at most 15 pages at a time."
        extracted = "\n".join((page.extract_text() or "") for page in doc.pages)
        if extracted.strip():
            return extracted, "Extracted embedded PDF text."
        try:
            import fitz
            import pytesseract
            with fitz.open(stream=data, filetype="pdf") as pdf:
                chunks = []
                for page in pdf:
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    img = Image.open(BytesIO(pix.tobytes("png")))
                    chunks.append(pytesseract.image_to_string(img))
            return "\n".join(chunks), "OCR applied to the scanned PDF."
        except Exception as exc:
            return "", (f"This looks like a scanned PDF. OCR couldn't run: {type(exc).__name__}. "
                        "Install Tesseract OCR (Windows) and ensure it is in PATH.")
    try:
        import pytesseract
        img = load_image(data)
        return pytesseract.image_to_string(img), "OCR applied to the uploaded report image."
    except Exception as exc:
        return "", (f"Image OCR couldn't run: {type(exc).__name__}. "
                    "Install Tesseract OCR and add it to PATH.")


if uploaded is None:
    st.caption("Select a category and upload a de-identified demo image to continue.")
    st.stop()
if uploaded.size > 12 * 1024 * 1024:
    st.error("File too large: 12 MB limit for the demonstration.")
    st.stop()
data = uploaded.getvalue()

if is_report:
    st.subheader("Health report reading")
    st.caption("This is text extraction + formula-based screening, NOT an image diagnosis or medical chatbot.")
    if not uploaded.name.lower().endswith(".pdf"):
        st.image(load_image(data), caption="Uploaded report", use_container_width=True)
    try:
        extracted, note = extract_report_text(data, uploaded.name)
    except Exception as exc:
        st.error(f"Report parsing failed: {type(exc).__name__}: {exc}")
        st.stop()
    if note:
        st.caption(note)
    if not extracted.strip():
        st.warning("No readable text found. Try a text-based PDF, or install Tesseract for scanned images.")
        st.stop()
    with st.expander("Review extracted text"):
        st.text_area("Extracted text", extracted[:20000], height=220)
    values = extract_candidate_lab_values(extracted)
    if not values:
        st.warning("No supported measurements were extracted. No conclusions will be generated.")
        st.stop()
    df = pd.DataFrame([{"Measurement (expected units)": name, "Candidate value": val} for name, val in values.items()])
    st.write("**Review each extracted number and its unit carefully.** OCR can misread decimals and units.")
    changed = st.data_editor(df, disabled=["Measurement (expected units)"], hide_index=True, use_container_width=True)
    sex = st.selectbox("Adult sex used in reference equation", ["Female", "Male"])
    age = st.number_input("Age (years)", 18, 120, 40)
    verified = st.checkbox("I have verified every extracted measurement and its units in the original report.")
    if st.button("Calculate supported educational screens", disabled=not verified):
        pairs = {}
        for _, row in changed.iterrows():
            try:
                pairs[row["Measurement (expected units)"]] = float(row["Candidate value"])
            except (TypeError, ValueError):
                continue
        if "Haemoglobin (g/dL)" in pairs:
            r = assess_haemoglobin(pairs["Haemoglobin (g/dL)"], "Non-pregnant woman" if sex == "Female" else "Man")
            st.info(f"Haemoglobin screening: {r['label']} — {r['detail']}")
        if "Creatinine (mg/dL)" in pairs:
            gfr = egfr_2021(age, pairs["Creatinine (mg/dL)"], sex)
            r = assess_egfr(gfr)
            st.info(f"Estimated filtration rate: {gfr:.1f} — {r['label']} — {r['detail']}")
        if "LDL (mg/dL)" in pairs:
            r = assess_ldl(pairs["LDL (mg/dL)"])
            st.info(f"LDL screening: {r['label']} — {r['detail']}")
        st.caption("All other extracted values are displayed for review only. Talk to a healthcare professional about abnormal results.")

    from result_explanations import explain_report
    explain_report(values, verified)
    st.stop()

image = load_image(data)
st.image(image, caption="Uploaded research image", use_container_width=True)
st.caption(f"Image resolution: {image.width} × {image.height}. The file type or body part is NOT verified automatically.")
spec = lookup_model(modality, part)
st.subheader("Research image classifier")
if spec is None:
    st.warning(
        f"No compatible research classifier is installed for **{modality} / {part}**. "
        "This category supports preview only; the app will not invent a diagnosis."
    )
    st.stop()
st.success(f"**Available:** {spec.label}")
st.write(f"**Trained on:** {spec.trained_on}")
st.warning(f"**Known limitations:** {spec.limitation}")
st.caption(f"Public model: https://huggingface.co/{spec.repo_id} · Declared model licence: {spec.license}")
agree = st.checkbox(
    "I understand this is an experimental model score, not a disease probability, and will not use it for medical decisions."
)
if st.button("Run research image model", disabled=not agree, type="primary"):
    try:
        with st.spinner("Downloading model on first use / running local inference. This could take several minutes …"):
            ranked = infer(image, spec)
        st.subheader("Experimental classifier label scores")
        scores = pd.DataFrame([{"Model label": label, "Uncalibrated softmax score": round(score, 4)}
                               for label, score in ranked])
        st.dataframe(scores, hide_index=True, use_container_width=True)
        st.bar_chart(scores.set_index("Model label"))
        st.error("These values are NOT diagnostic confidence or patient disease probabilities. A high score may still be wrong.")
        st.session_state["mp_ax_imaging_result"] = {"route": (modality,part), "ranked": ranked}
    except ImportError as exc:
        st.error(f"Required model dependency is missing: {exc}. Run the model-requirements install command.")
    except Exception as exc:
        st.error("Unable to run this model. Check internet, Hugging Face availability, available memory and installed package versions.")
        st.code(f"{type(exc).__name__}: {exc}")



mp_ax_last = st.session_state.get('mp_ax_imaging_result')
if mp_ax_last and mp_ax_last.get('route') == (modality,part):
    from result_explanations import explain_imaging
    explain_imaging(mp_ax_last['ranked'],spec,image)

st.divider()
if st.button("← Back to MedPredict dashboard"):
    st.switch_page("app.py")
