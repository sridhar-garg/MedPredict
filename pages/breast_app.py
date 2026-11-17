import streamlit as st
import pandas as pd
import joblib

from database import save_health_assessment
from pathlib import Path

from utils import (
    display_prediction,
    readable_feature,
    breast_default,
    apply_common_style,
)






st.set_page_config(
    page_title="Breast Cancer Risk Assessment",
    page_icon="🎗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


from sidebar_compat import show_sidebar
show_sidebar()

apply_common_style()

MODEL_DIR = Path("models")






def load_models(filename):
    return joblib.load(MODEL_DIR / filename)


def load_features(filename):
    return joblib.load(MODEL_DIR / filename)


def step_for(value):
    if value < 0.01:
        return 0.001
    if value < 1:
        return 0.01
    if value < 10:
        return 0.1
    return 1.0






st.markdown(
    """
    <div class="section-heading">
        <span class="section-number">01</span>
        <div>
            <h2>Breast Cancer Risk Assessment</h2>
            <p>Enter tumor measurements from a diagnostic report.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Enter measurements from a diagnostic report. "
    "The trained model uses these tumor characteristics to estimate risk. "
    "This result is a research/academic estimate, not a diagnosis."
)






try:
    breast_models = load_models("breast_models.pkl")
    breast_features = load_features("breast_features.pkl")

except Exception as e:
    st.error("Could not load breast cancer model files.")
    st.code(str(e))
    st.stop()






groups = [
    (
        "Tumor Characteristics",
        "Average measurements describing the size and shape of the tumor.",
        breast_features[:10],
    ),
    (
        "Measurement Error",
        "Variation/error values associated with the corresponding measurements.",
        breast_features[10:20],
    ),
    (
        "Worst / Maximum Measurements",
        "The largest or most severe measurement recorded for each tumor feature.",
        breast_features[20:30],
    ),
]

patient_values = {}

for group_title, group_description, features in groups:

    st.markdown(
        f"""
        <div class="breast-measurement-card">
            <h3>{group_title}</h3>
            <p>{group_description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(3)

    for index, feature in enumerate(features):

        default = float(breast_default(feature))

        with cols[index % 3]:
            patient_values[feature] = st.number_input(
                readable_feature(feature),
                value=default,
                step=step_for(default),
                format="%.6f",
                key=f"breast_input_{feature}",
                help=(
                    "UI starting value only. "
                    "Use the value from the diagnostic report."
                ),
            )






st.markdown(
    """
    <div class="assessment-section-card">
        <div class="assessment-section-title">Run the AI Assessment</div>
        <div class="assessment-section-subtitle">
            The entered measurements will be evaluated by the saved
            machine-learning models.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button(
    "🧠 Analyze Breast Cancer Risk →",
    type="primary",
    use_container_width=True,
):

    patient = pd.DataFrame(
        [[patient_values[f] for f in breast_features]],
        columns=breast_features,
    )

    result = display_prediction(
        breast_models,
        patient,
        "Breast Cancer",
    )

    if result is not None:

        from result_explanations import explain_prediction
        explain_prediction(result, 'breast cancer')

        user_id = st.session_state.get("user_id")

        if user_id is not None:

            try:
                saved = save_health_assessment(
                    user_id=user_id,
                    disease="Breast Cancer",
                    input_data=patient_values,
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
                    "The prediction was completed, but the result "
                    "could not be saved."
                )
                st.code(str(e))

        else:
            st.warning(
                "You are not logged in, so this assessment "
                "was not saved to your health history."
            )












st.markdown(
    """
    <div class="workflow-heading-fixed">
        <span class="workflow-heading-icon">⌁</span>
        <div>
            <h2>How this assessment works</h2>
            <p>From diagnostic measurements to an explainable AI result.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

workflow_cols = st.columns([1, 0.15, 1, 0.15, 1, 0.15, 1])

steps = [
    (
        "01",
        "Enter Measurements",
        "Provide the values from the diagnostic report.",
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
