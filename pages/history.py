import json
from datetime import datetime, timezone
from textwrap import dedent
from zoneinfo import ZoneInfo

import streamlit as st

from database import get_health_assessments
from utils import apply_custom_css






st.set_page_config(
    page_title="Health History | HealthAI",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)


from sidebar_compat import show_sidebar
show_sidebar()






if "healthai_theme" not in st.session_state:
    st.session_state.healthai_theme = "light"

apply_custom_css()






if not st.session_state.get("is_logged_in", False):
    st.warning("Please log in to view your health history.")
    st.stop()


user_id = st.session_state.get("user_id")

if user_id is None:
    st.error("User session could not be found.")
    st.stop()






st.html(
    dedent(
        """
        <div class="section-heading">
            <span class="section-number">04</span>
            <div>
                <h2>Health History</h2>
                <p>
                    Review your previous health assessments and
                    AI-generated evaluations.
                </p>
            </div>
        </div>
        """
    ),
)






try:
    assessments = get_health_assessments(user_id)
except Exception as e:
    st.error("Unable to load your health history.")
    st.code(str(e))
    st.stop()






if not assessments:
    st.html(
        dedent(
            """
            <div class="assessment-section-card">
                <div class="assessment-section-title">
                    📋 No Assessments Yet
                </div>
                <div class="assessment-section-subtitle">
                    You haven't completed any health assessments yet.
                    Your Breast Cancer, Diabetes, and Heart Disease
                    assessments will appear here after you complete them.
                </div>
            </div>
            """
        ),
    )

    st.info(
        "Start an assessment from the Dashboard to build your personal health history."
    )
    st.stop()






total_assessments = len(assessments)

breast_count = sum(
    1 for assessment in assessments
    if str(assessment[1]).strip().lower() == "breast cancer"
)

diabetes_count = sum(
    1 for assessment in assessments
    if str(assessment[1]).strip().lower() == "diabetes"
)

heart_count = sum(
    1 for assessment in assessments
    if str(assessment[1]).strip().lower() == "heart disease"
)






st.html(
    dedent(
        """
        <div class="assessment-section-card">
            <div class="assessment-section-title">
                📊 Assessment Summary
            </div>
            <div class="assessment-section-subtitle">
                A quick overview of your completed AI health assessments.
            </div>
        </div>
        """
    ),
)

summary1, summary2, summary3, summary4 = st.columns(4)

with summary1:
    st.metric("Total Assessments", total_assessments)

with summary2:
    st.metric("Breast Cancer", breast_count)

with summary3:
    st.metric("Diabetes", diabetes_count)

with summary4:
    st.metric("Heart Disease", heart_count)






st.markdown("<br>", unsafe_allow_html=True)

available_diseases = [
    "All Diseases",
    "Breast Cancer",
    "Diabetes",
    "Heart Disease",
]

present_diseases = {
    str(assessment[1]).strip()
    for assessment in assessments
}

diseases = [
    disease
    for disease in available_diseases
    if disease == "All Diseases" or disease in present_diseases
]

selected_disease = st.selectbox(
    "Filter by disease",
    diseases,
    key="history_disease_filter",
)






if selected_disease == "All Diseases":
    filtered_assessments = assessments
else:
    filtered_assessments = [
        assessment
        for assessment in assessments
        if str(assessment[1]).strip() == selected_disease
    ]






st.html(
    dedent(
        """
        <div class="section-heading">
            <span class="section-number">05</span>
            <div>
                <h2>Previous Assessments</h2>
                <p>
                    Open an assessment to view the submitted information
                    and AI evaluation.
                </p>
            </div>
        </div>
        """
    ),
)


if not filtered_assessments:
    st.info(
        f"No {selected_disease.lower()} assessments were found."
    )
    st.stop()






def display_assessment_value(disease, key, value):
    """
    Convert stored model-friendly values into human-readable values
    without changing anything stored in the database or sent to models.
    """
    disease_name = str(disease).strip().lower()
    key_name = str(key).strip().lower().replace("_", " ")


    numeric_value = None
    try:
        numeric_value = int(float(value))
    except (TypeError, ValueError):
        pass


    if disease_name == "diabetes":
        if key_name == "gender":
            if numeric_value in (0, 1):
                return "Male" if numeric_value == 1 else "Female"

        diabetes_binary_fields = {
            "polyuria",
            "polydipsia",
            "sudden weight loss",
            "weakness",
            "polyphagia",
            "genital thrush",
            "visual blurring",
            "itching",
            "irritability",
            "delayed healing",
            "partial paresis",
            "muscle stiffness",
            "alopecia",
            "obesity",
        }

        if key_name in diabetes_binary_fields and numeric_value in (0, 1):
            return "Yes" if numeric_value == 1 else "No"


    if disease_name == "breast cancer":
        breast_binary_fields = {
            "mean radius",
            "mean texture",
            "mean perimeter",
            "mean area",
            "mean smoothness",
            "mean compactness",
            "mean concavity",
            "mean concave points",
            "mean symmetry",
            "mean fractal dimension",
            "radius error",
            "texture error",
            "perimeter error",
            "area error",
            "smoothness error",
            "compactness error",
            "concavity error",
            "concave points error",
            "symmetry error",
            "fractal dimension error",
            "worst radius",
            "worst texture",
            "worst perimeter",
            "worst area",
            "worst smoothness",
            "worst compactness",
            "worst concavity",
            "worst concave points",
            "worst symmetry",
            "worst fractal dimension",
        }



        if key_name in breast_binary_fields:
            return value


    if disease_name == "heart disease":
        heart_binary_fields = {
            "sex",
            "fbs",
            "exang",
            "target",
            "smoking",
            "smoker",
            "diabetes",
            "hypertension",
        }

        if key_name in heart_binary_fields and numeric_value in (0, 1):



            yes_no_fields = {
                "smoking",
                "smoker",
                "diabetes",
                "hypertension",
            }
            if key_name in yes_no_fields:
                return "Yes" if numeric_value == 1 else "No"

            if key_name == "sex":
                return "Male" if numeric_value == 1 else "Female"


    if isinstance(value, bool):
        return "Yes" if value else "No"

    return value






for assessment in filtered_assessments:

    (
        assessment_id,
        disease,
        input_data,
        prediction,
        probability,
        evaluation,
        created_at,
    ) = assessment




    try:


        utc_time = datetime.fromisoformat(str(created_at))

        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)

        ist_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))


        date_value = ist_time.strftime("%d %B %Y, %I:%M:%S %p")

    except Exception:
        date_value = str(created_at)





    if probability is not None:
        try:
            probability_text = (
                f"{float(probability) * 100:.2f}%"
            )
        except (TypeError, ValueError):
            probability_text = str(probability)
    else:
        probability_text = "N/A"

    prediction_text = (
        str(prediction)
        if prediction is not None
        else "Not available"
    )





    st.html(
        dedent(
            f"""
            <div class="assessment-section-card">
                <div class="assessment-section-title">
                    {disease}
                </div>

                <div class="assessment-section-subtitle">
                    📅 {date_value}
                </div>

                <hr>

                <p>
                    <strong>AI Result:</strong>
                    {prediction_text}
                </p>

                <p>
                    <strong>Estimated Probability:</strong>
                    {probability_text}
                </p>
            </div>
            """
        ),
    )





    with st.expander(
        f"View {disease} Assessment Details"
    ):

        st.markdown("#### 🧾 Assessment Information")

        if input_data:

            try:
                if isinstance(input_data, str):
                    parsed_input = json.loads(input_data)
                else:
                    parsed_input = input_data

                if isinstance(parsed_input, dict):

                    input_columns = st.columns(2)

                    for index, (key, value) in enumerate(
                        parsed_input.items()
                    ):

                        readable_key = (
                            str(key)
                            .replace("_", " ")
                            .replace("-", " ")
                            .title()
                        )

                        display_value = display_assessment_value(
                            disease,
                            key,
                            value,
                        )

                        with input_columns[index % 2]:
                            st.html(
                                dedent(
                                    f"""
                                    <div class="assessment-section-card">
                                        <div class="assessment-section-subtitle">
                                            {readable_key}
                                        </div>
                                        <div class="assessment-section-title">
                                            {display_value}
                                        </div>
                                    </div>
                                    """
                                ),
                            )

                else:
                    st.write(parsed_input)

            except Exception:
                st.code(str(input_data))

        else:
            st.info("No assessment input data was stored.")





        st.markdown("#### 🤖 AI Evaluation")

        if evaluation:
            st.html(
                dedent(
                    f"""
                    <div class="assessment-section-card">
                        <div class="assessment-section-subtitle">
                            Model Evaluation
                        </div>
                        <div style="margin-top: 8px;">
                            {evaluation}
                        </div>
                    </div>
                    """
                ),
            )
        else:
            st.info(
                "No AI evaluation text was stored for this assessment."
            )

        st.caption(
            f"Assessment ID: {assessment_id}"
        )






st.html(
    dedent(
        """
        <div class="healthai-footer-note">
            <span>♥</span>
            HealthAI &nbsp;•&nbsp;
            Personal Health Assessment History &nbsp;•&nbsp;
            AI Risk Assessment
        </div>
        """
    ),
)
