"""Seven additional evidence-informed *screening* modules for MedPredict.

No trained ML is claimed here: these are transparent, source-linked formulas
and classifications. Results are not diagnoses or treatment advice.
"""

from utils import apply_custom_css
import streamlit as st
from medical_addon_core import (
    SOURCES, assess_bp, egfr_2021, assess_egfr, assess_haemoglobin,
    assess_ldl, assess_bmi, assess_stop_bang, fib4, assess_fib4,
)

st.set_page_config(page_title="More Health Screenings | MedPredict", page_icon="🩺", layout="wide", initial_sidebar_state="expanded")


from sidebar_compat import show_sidebar
show_sidebar()


apply_custom_css()
if not st.session_state.get("is_logged_in", False):
    st.warning("Please sign in to access health screenings.")
    if st.button("Open login"):
        st.switch_page("app.py")
    st.stop()

st.title("🩺 Seven More Health Screenings")
st.caption("Educational screening tools, not diagnostic AI. Inputs are not automatically saved to your existing patient database.")
st.warning("For adult users and demonstration purposes. Do not use these results for diagnosis, medication decisions, or emergencies. A healthcare professional must interpret findings and symptoms.")

CONDITIONS = [
    "High blood pressure", "Chronic kidney disease indicators", "Anaemia indicators",
    "High LDL cholesterol", "Obesity / BMI", "Sleep apnoea screening", "Liver fibrosis screening",
]
choice = st.selectbox("Choose a screening tool", CONDITIONS)


def show_result(result, metric=None, source=None):
    st.subheader("Screening result")
    if metric:
        st.metric(metric[0], metric[1])
    getattr(st, result["level"])("**" + result["label"] + "** — " + result["detail"])
    st.caption("This output is a category or score, NOT a disease probability or a diagnosis.")
    if source:
        st.markdown(f"[Clinical reference]({SOURCES[source]})")

    from result_explanations import explain_screening
    explain_screening(result,metric,SOURCES.get(source) if source else None)


if choice == "High blood pressure":
    st.write("Enter a correctly measured adult blood pressure. Categories follow the American Heart Association.")
    with st.form("bp"):
        sys = st.number_input("Systolic BP (mmHg)", 40, 300, 120)
        dia = st.number_input("Diastolic BP (mmHg)", 20, 200, 80)
        go = st.form_submit_button("Assess reading")
    if go:
        show_result(assess_bp(sys, dia), ("BP", f"{sys}/{dia} mmHg"), "blood_pressure")

elif choice == "Chronic kidney disease indicators":
    st.write("Uses the 2021 CKD-EPI creatinine-based estimate. Only appropriate for adults with a lab-tested creatinine value.")
    with st.form("kidney"):
        age = st.number_input("Age", 18, 120, 40)
        sex = st.selectbox("Sex coefficient used by lab equation", ["Female", "Male"])
        cr = st.number_input("Serum creatinine (mg/dL)", min_value=0.1, max_value=25.0, value=1.0, step=0.1)
        go = st.form_submit_button("Calculate eGFR")
    if go:
        value = egfr_2021(age, cr, sex)
        show_result(assess_egfr(value), ("Estimated GFR", f"{value:.1f} mL/min/1.73m²"), "kidney")
        st.info("CKD cannot be confirmed by one eGFR. Persistence for at least 3 months and/or markers such as urine albumin are important.")

elif choice == "Anaemia indicators":
    st.write("Uses selected WHO 2024 haemoglobin thresholds for nonpregnant adults aged 18–65. Other ages and pregnancy require different cutoffs.")
    with st.form("anemia"):
        group = st.selectbox("Group", ["Non-pregnant woman", "Man"])
        hb = st.number_input("Measured haemoglobin (g/dL)", min_value=1.0, max_value=25.0, value=13.0, step=0.1)
        go = st.form_submit_button("Interpret haemoglobin")
    if go:
        show_result(assess_haemoglobin(hb, group), ("Haemoglobin", f"{hb:.1f} g/dL"), "anaemia")

elif choice == "High LDL cholesterol":
    st.write("Conventional LDL cholesterol bands are descriptive, not personalised cardiovascular risk estimates.")
    with st.form("lipids"):
        ldl = st.number_input("Laboratory LDL cholesterol (mg/dL)", min_value=0.0, max_value=500.0, value=105.0, step=1.0)
        go = st.form_submit_button("Review LDL category")
    if go:
        show_result(assess_ldl(ldl), ("LDL cholesterol", f"{ldl:.0f} mg/dL"), "cholesterol")

elif choice == "Obesity / BMI":
    st.write("Adult BMI is an indirect measurement and cannot diagnose metabolic illness on its own.")
    with st.form("bmi"):
        height = st.number_input("Height (cm)", min_value=90.0, max_value=250.0, value=170.0)
        weight = st.number_input("Weight (kg)", min_value=10.0, max_value=450.0, value=70.0)
        go = st.form_submit_button("Calculate BMI")
    if go:
        value, result = assess_bmi(height, weight)
        show_result(result, ("Body mass index", f"{value:.1f} kg/m²"), "bmi")

elif choice == "Sleep apnoea screening":
    st.write("STOP-BANG is a screening questionnaire. It does not confirm sleep apnoea; sleep studies can be required.")
    with st.form("stopbang"):
        questions = [
            "S: Do you snore loudly?",
            "T: Do you often feel tired or sleepy in daytime?",
            "O: Has someone observed you stop breathing during sleep?",
            "P: Do you have or receive treatment for high blood pressure?",
            "B: Is your BMI greater than 35 kg/m²?",
            "A: Are you older than 50 years?",
            "N: Is your neck circumference greater than 40 cm?",
            "G: Male sex as used in the original questionnaire?",
        ]
        responses = [st.checkbox(q, key=f"sb_{i}") for i, q in enumerate(questions)]
        go = st.form_submit_button("Calculate screening score")
    if go:
        value, result = assess_stop_bang(responses)
        show_result(result, ("STOP-BANG score", f"{value}/8"), "sleep")

else:
    st.write("The FIB-4 score estimates advanced fibrosis risk in selected adults with suspected or known chronic liver/metabolic liver conditions. It does not detect all liver diseases.")
    with st.form("fib4"):
        age = st.number_input("Age", 18, 120, 45)
        ast = st.number_input("AST (U/L)", min_value=1.0, max_value=1500.0, value=30.0)
        alt = st.number_input("ALT (U/L)", min_value=1.0, max_value=1500.0, value=30.0)
        platelets = st.number_input("Platelets (×10⁹/L)", min_value=1.0, max_value=1000.0, value=220.0)
        go = st.form_submit_button("Calculate FIB-4")
    if go:
        value = fib4(age, ast, alt, platelets)
        show_result(assess_fib4(age, value), ("FIB-4 score", f"{value:.2f}"), "liver")

st.divider()
if st.button("← Back to MedPredict home"):
    st.switch_page("app.py")
