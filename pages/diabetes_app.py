import streamlit as st
import pandas as pd
import joblib
from pathlib import Path

from utils import display_prediction, apply_common_style
from database import save_health_assessment






st.set_page_config(
    page_title="Diabetes Risk Assessment",
    page_icon="🩸",
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


def yes_no(value):
    return 1 if value == "Yes" else 0






st.markdown(
    """
    <div class="section-heading">
        <span class="section-number">01</span>
        <div>
            <h2>Diabetes Risk Assessment</h2>
            <p>Enter basic information and reported symptoms.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)






try:
    diabetes_models = load_models("diabetes_models.pkl")
    diabetes_features = load_features("diabetes_features.pkl")
except Exception as e:
    st.error("Could not load diabetes model files.")
    st.code(str(e))
    st.stop()






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">👤 Basic Information</div>
        <div class="assessment-section-subtitle">
            Enter the patient's basic demographic information.
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
        value=40,
        key="diabetes_age",
    )

with col2:
    gender = st.selectbox(
        "Gender",
        ["Male", "Female"],
        key="diabetes_gender",
    )






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">
            🩺 Symptoms & Health Indicators
        </div>
        <div class="assessment-section-subtitle">
            Select the symptoms or conditions reported for the patient.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    polyuria = st.selectbox(
        "Polyuria — frequent urination",
        ["No", "Yes"],
        key="diabetes_polyuria",
    )

    sudden_weight_loss = st.selectbox(
        "Sudden weight loss",
        ["No", "Yes"],
        key="diabetes_weight_loss",
    )

    polyphagia = st.selectbox(
        "Polyphagia — excessive hunger",
        ["No", "Yes"],
        key="diabetes_polyphagia",
    )

    visual_blurring = st.selectbox(
        "Visual blurring",
        ["No", "Yes"],
        key="diabetes_visual_blurring",
    )

    irritability = st.selectbox(
        "Irritability",
        ["No", "Yes"],
        key="diabetes_irritability",
    )

    partial_paresis = st.selectbox(
        "Partial paresis",
        ["No", "Yes"],
        key="diabetes_partial_paresis",
    )

    alopecia = st.selectbox(
        "Alopecia — hair loss",
        ["No", "Yes"],
        key="diabetes_alopecia",
    )

    obesity = st.selectbox(
        "Obesity",
        ["No", "Yes"],
        key="diabetes_obesity",
    )

with col2:
    polydipsia = st.selectbox(
        "Polydipsia — excessive thirst",
        ["No", "Yes"],
        key="diabetes_polydipsia",
    )

    weakness = st.selectbox(
        "Weakness",
        ["No", "Yes"],
        key="diabetes_weakness",
    )

    genital_thrush = st.selectbox(
        "Genital thrush",
        ["No", "Yes"],
        key="diabetes_genital_thrush",
    )

    itching = st.selectbox(
        "Itching",
        ["No", "Yes"],
        key="diabetes_itching",
    )

    delayed_healing = st.selectbox(
        "Delayed healing",
        ["No", "Yes"],
        key="diabetes_delayed_healing",
    )

    muscle_stiffness = st.selectbox(
        "Muscle stiffness",
        ["No", "Yes"],
        key="diabetes_muscle_stiffness",
    )






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">Run the AI Assessment</div>
        <div class="assessment-section-subtitle">
            The entered information will be evaluated by the saved
            machine-learning models.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button(
    "🧠 Analyze Diabetes Risk →",
    type="primary",
    use_container_width=True,
    key="diabetes_analyze_button",
):
    raw_patient = {
        "age": age,
        "gender": 1 if gender == "Male" else 0,
        "polyuria": yes_no(polyuria),
        "polydipsia": yes_no(polydipsia),
        "sudden weight loss": yes_no(sudden_weight_loss),
        "weakness": yes_no(weakness),
        "polyphagia": yes_no(polyphagia),
        "genital thrush": yes_no(genital_thrush),
        "visual blurring": yes_no(visual_blurring),
        "itching": yes_no(itching),
        "irritability": yes_no(irritability),
        "delayed healing": yes_no(delayed_healing),
        "partial paresis": yes_no(partial_paresis),
        "muscle stiffness": yes_no(muscle_stiffness),
        "alopecia": yes_no(alopecia),
        "obesity": yes_no(obesity),
    }

    patient = pd.DataFrame([raw_patient]).reindex(
        columns=diabetes_features
    )

    result = display_prediction(
        diabetes_models,
        patient,
        "Diabetes",
    )

    if result is not None:

        from result_explanations import explain_prediction
        explain_prediction(result, 'diabetes')
        user_id = st.session_state.get("user_id")

        if user_id is not None:
            try:
                saved = save_health_assessment(
                    user_id=user_id,
                    disease="Diabetes",
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
                <p>From reported information to an explainable AI result.</p>
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
        "Provide the patient's basic information and symptoms.",
    ),
    (
        "02",
        "Five AI Models",
        "Multiple trained models analyze the same information.",
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
