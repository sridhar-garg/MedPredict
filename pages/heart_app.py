import streamlit as st
import pandas as pd
import joblib
from pathlib import Path

from utils import display_prediction, apply_common_style
from database import save_health_assessment






st.set_page_config(
    page_title="Heart Disease Risk Assessment",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="collapsed",
)


from sidebar_compat import show_sidebar
show_sidebar()

apply_common_style()


st.markdown(
    """
    <style>
    div.stButton {
        width: 100% !important;
    }

    div.stButton > button {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        min-height: 52px !important;
        white-space: nowrap !important;
        writing-mode: horizontal-tb !important;
        text-orientation: mixed !important;
        transform: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
    }

    div.stButton > button p {
        white-space: nowrap !important;
        writing-mode: horizontal-tb !important;
        text-orientation: mixed !important;
        margin: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MODEL_DIR = Path("models")






def load_models(filename):
    return joblib.load(MODEL_DIR / filename)


def load_features(filename):
    return joblib.load(MODEL_DIR / filename)






st.markdown(
    """
    <div class="section-heading">
        <span class="section-number">01</span>
        <div>
            <h2>Heart Disease Risk Assessment</h2>
            <p>Enter the patient's cardiovascular measurements and clinical information.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)






try:
    heart_models = load_models("heart_models.pkl")
    heart_features = load_features("heart_features.pkl")
except Exception as e:
    st.error("Could not load heart disease model files.")
    st.code(str(e))
    st.stop()






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">🩺 Clinical Information</div>
        <div class="assessment-section-subtitle">
            Basic cardiovascular and resting measurements.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    age = st.number_input(
        "Age",
        min_value=1,
        max_value=120,
        value=50,
        key="heart_age",
    )

    sex = st.selectbox(
        "Sex",
        ["Female", "Male"],
        key="heart_sex",
    )

    cp = st.selectbox(
        "Chest Pain Type",
        [
            "Typical angina",
            "Atypical angina",
            "Non-anginal pain",
            "Asymptomatic",
        ],
        help="The category is converted to the numeric value expected by the trained model.",
        key="heart_cp",
    )

    trestbps = st.number_input(
        "Resting Blood Pressure (mm Hg)",
        min_value=50.0,
        max_value=250.0,
        value=120.0,
        key="heart_trestbps",
    )

    chol = st.number_input(
        "Cholesterol (mg/dl)",
        min_value=50.0,
        max_value=700.0,
        value=200.0,
        key="heart_chol",
    )

    fbs = st.selectbox(
        "Fasting Blood Sugar > 120 mg/dl",
        ["No", "Yes"],
        key="heart_fbs",
    )

with col2:
    restecg = st.selectbox(
        "Resting ECG",
        [
            "Normal",
            "ST-T wave abnormality",
            "Left ventricular hypertrophy",
        ],
        key="heart_restecg",
    )

    thalach = st.number_input(
        "Maximum Heart Rate Achieved",
        min_value=50.0,
        max_value=250.0,
        value=150.0,
        key="heart_thalach",
    )

    exang = st.selectbox(
        "Exercise-Induced Angina",
        ["No", "Yes"],
        key="heart_exang",
    )

    oldpeak = st.number_input(
        "ST Depression (Oldpeak)",
        min_value=0.0,
        max_value=10.0,
        value=1.0,
        step=0.1,
        key="heart_oldpeak",
    )

    slope = st.selectbox(
        "Slope of Peak Exercise ST",
        ["Upsloping", "Flat", "Downsloping"],
        key="heart_slope",
    )

    ca = st.number_input(
        "Number of Major Vessels (0–4)",
        min_value=0,
        max_value=4,
        value=0,
        key="heart_ca",
    )

    thal = st.selectbox(
        "Thalassemia",
        ["Normal", "Fixed defect", "Reversible defect"],
        key="heart_thal",
    )






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">Run the AI Assessment</div>
        <div class="assessment-section-subtitle">
            The entered clinical information will be evaluated by the saved
            machine-learning models.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button(
    "🧠 Analyze Heart Disease Risk →",
    type="primary",
    use_container_width=True,
    key="heart_analyze_button",
):
    cp_value = {
        "Typical angina": 0,
        "Atypical angina": 1,
        "Non-anginal pain": 2,
        "Asymptomatic": 3,
    }[cp]

    restecg_value = {
        "Normal": 0,
        "ST-T wave abnormality": 1,
        "Left ventricular hypertrophy": 2,
    }[restecg]

    slope_value = {
        "Upsloping": 0,
        "Flat": 1,
        "Downsloping": 2,
    }[slope]

    thal_value = {
        "Normal": 1,
        "Fixed defect": 2,
        "Reversible defect": 3,
    }[thal]

    raw_patient = {
        "age": age,
        "sex": 1 if sex == "Male" else 0,
        "cp": cp_value,
        "trestbps": trestbps,
        "chol": chol,
        "fbs": 1 if fbs == "Yes" else 0,
        "restecg": restecg_value,
        "thalach": thalach,
        "exang": 1 if exang == "Yes" else 0,
        "oldpeak": oldpeak,
        "slope": slope_value,
        "ca": ca,
        "thal": thal_value,
    }

    patient = pd.DataFrame([raw_patient]).reindex(columns=heart_features)

    result = display_prediction(
        heart_models,
        patient,
        "Heart Disease",
    )

    if result is not None:

        from result_explanations import explain_prediction
        explain_prediction(result, 'heart disease')
        user_id = st.session_state.get("user_id")

        if user_id is not None:
            try:
                saved = save_health_assessment(
                    user_id=user_id,
                    disease="Heart Disease",
                    input_data=raw_patient,
                    prediction=result["risk_category"],
                    probability=result["probability"],
                    evaluation=result["evaluation"],
                )

                if saved:
                    st.success(
                        "Assessment saved successfully to your health history."
                    )

            except Exception as e:
                st.error(
                    "The prediction was completed, but the result could not be saved."
                )
                st.code(str(e))
        else:
            st.warning(
                "You are not logged in, so this assessment was not saved "
                "to your health history."
            )






st.markdown(
    """
    <div class="healthai-workflow">
        <div class="workflow-title">
            <span>⌁</span>
            <div>
                <h2>How this assessment works</h2>
                <p>From clinical measurements to an explainable AI result.</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

workflow_cols = st.columns([1, 0.15, 1, 0.15, 1, 0.15, 1])

steps = [
    (
        "01",
        "Enter Information",
        "Provide the patient's cardiovascular measurements.",
    ),
    (
        "02",
        "Five AI Models",
        "Multiple trained models analyze the same measurements.",
    ),
    (
        "03",
        "Compare Results",
        "The available model probabilities are combined into an overall estimate.",
    ),
    (
        "04",
        "Explain with XAI",
        "SHAP identifies the features that influenced the model result.",
    ),
]

for i, (number, title, description) in enumerate(steps):
    with workflow_cols[i * 2]:
        st.markdown(
            f"""
            <div class="workflow-step">
                <span>{number}</span>
                <div>
                    <b>{title}</b>
                    <p>{description}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if i < 3:
        with workflow_cols[i * 2 + 1]:
            st.markdown(
                '<div class="workflow-arrow">→</div>',
                unsafe_allow_html=True,
            )
