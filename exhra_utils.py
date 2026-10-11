import streamlit as st
import pandas as pd
import numpy as np
import joblib
import shap


MODEL_DIR = "models"






@st.cache_resource
def load_models(filename):
    return joblib.load(f"{MODEL_DIR}/{filename}")


@st.cache_resource
def load_features(filename):
    return joblib.load(f"{MODEL_DIR}/{filename}")


def risk_category(probability):
    percentage = probability * 100

    if percentage < 30:
        return "LOW RISK"
    elif percentage < 70:
        return "MODERATE RISK"

    return "HIGH RISK"


def display_prediction(models, patient, disease_name):

    probabilities = []
    model_rows = []

    for name, model in models.items():

        try:
            probability = float(
                model.predict_proba(patient)[0][1]
            )

        except Exception as e:
            st.error(
                f"{name} could not make a prediction."
            )
            st.code(str(e))
            return

        probabilities.append(probability)

        model_rows.append(
            {
                "Model": name,
                "Risk Probability":
                    f"{probability * 100:.1f}%"
            }
        )

    if not probabilities:
        st.error("No trained models were found.")
        return

    risk_probability = float(
        np.mean(probabilities)
    )

    risk_percentage = risk_probability * 100

    risk_level = risk_category(
        risk_probability
    )

    st.divider()

    st.header("📊 Assessment Result")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Estimated Risk",
            f"{risk_percentage:.1f}%"
        )

    with col2:
        st.metric(
            "Risk Category",
            risk_level
        )

    st.progress(
        min(
            max(risk_probability, 0.0),
            1.0
        )
    )

    if risk_level == "LOW RISK":

        st.success(
            "The model estimates a relatively low risk "
            "based on the entered information."
        )

    elif risk_level == "MODERATE RISK":

        st.warning(
            "The model estimates a moderate level of risk "
            "based on the entered information."
        )

    else:

        st.error(
            "The model estimates a high level of risk "
            "based on the entered information."
        )

    st.subheader("🤖 Model Predictions")

    st.dataframe(
        pd.DataFrame(model_rows),
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "The displayed risk is the average probability "
        "produced by the five trained models."
    )





    st.subheader("🔎 Explainable AI")

    if "Random Forest" in models:

        show_shap_explanation(
            models["Random Forest"],
            patient,
            disease_name
        )

    else:

        st.info(
            "Random Forest model is not available for XAI."
        )


def show_shap_explanation(
    pipeline,
    patient,
    disease_name
):

    try:

        final_model = pipeline.named_steps["model"]

        transformer = pipeline[:-1]

        transformed_patient = transformer.transform(
            patient
        )

        if hasattr(
            transformer,
            "get_feature_names_out"
        ):

            feature_names = list(
                transformer.get_feature_names_out()
            )

        else:

            feature_names = list(
                patient.columns
            )

        explainer = shap.TreeExplainer(
            final_model
        )

        shap_values = explainer.shap_values(
            transformed_patient
        )

        if isinstance(shap_values, list):

            values = np.asarray(
                shap_values[-1]
            )[0]

        else:

            values = np.asarray(
                shap_values
            )

            if values.ndim == 3:

                values = values[
                    0,
                    :,
                    -1
                ]

            elif values.ndim == 2:

                values = values[0]

            else:

                values = values.flatten()

        values = np.asarray(
            values,
            dtype=float
        )

        n = min(
            len(feature_names),
            len(values)
        )

        explanation_df = pd.DataFrame(
            {
                "Feature":
                    feature_names[:n],

                "Contribution":
                    values[:n],

                "Absolute Contribution":
                    np.abs(values[:n])
            }
        )

        explanation_df = (
            explanation_df
            .sort_values(
                "Absolute Contribution",
                ascending=False
            )
        )

        top = explanation_df.head(
            10
        ).copy()

        top["Direction"] = np.where(
            top["Contribution"] >= 0,
            "Increases risk",
            "Decreases risk"
        )

        top["Contribution"] = (
            top["Contribution"]
            .map(
                lambda x:
                f"{x:.4f}"
            )
        )

        st.write(
            f"Top factors influencing the "
            f"{disease_name} Random Forest prediction:"
        )

        st.dataframe(
            top[
                [
                    "Feature",
                    "Contribution",
                    "Direction"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "SHAP contributions describe how the model "
            "output changes relative to its baseline. "
            "They are not causal medical explanations."
        )

    except Exception as e:

        st.warning(
            "The prediction worked, but the SHAP "
            "explanation could not be generated."
        )

        st.code(str(e))


def breast_default(feature):

    name = feature.lower().strip()

    defaults = {

        "radius_mean": 14.0,
        "mean_radius": 14.0,

        "texture_mean": 19.0,
        "mean_texture": 19.0,

        "perimeter_mean": 90.0,
        "mean_perimeter": 90.0,

        "area_mean": 600.0,
        "mean_area": 600.0,

        "smoothness_mean": 0.10,
        "mean_smoothness": 0.10,

        "compactness_mean": 0.10,
        "mean_compactness": 0.10,

        "concavity_mean": 0.08,
        "mean_concavity": 0.08,

        "concave points_mean": 0.05,
        "mean_concave_points": 0.05,

        "symmetry_mean": 0.18,
        "mean_symmetry": 0.18,

        "fractal_dimension_mean": 0.06,
        "mean_fractal_dimension": 0.06,

        "radius_se": 0.40,
        "radius_error": 0.40,

        "texture_se": 1.20,
        "texture_error": 1.20,

        "perimeter_se": 2.80,
        "perimeter_error": 2.80,

        "area_se": 40.0,
        "area_error": 40.0,

        "smoothness_se": 0.007,
        "smoothness_error": 0.007,

        "compactness_se": 0.025,
        "compactness_error": 0.025,

        "concavity_se": 0.03,
        "concavity_error": 0.03,

        "concave points_se": 0.012,
        "concave_points_error": 0.012,

        "symmetry_se": 0.02,
        "symmetry_error": 0.02,

        "fractal_dimension_se": 0.004,
        "fractal_dimension_error": 0.004,

        "radius_worst": 16.0,
        "worst_radius": 16.0,

        "texture_worst": 25.0,
        "worst_texture": 25.0,

        "perimeter_worst": 105.0,
        "worst_perimeter": 105.0,

        "area_worst": 800.0,
        "worst_area": 800.0,

        "smoothness_worst": 0.14,
        "worst_smoothness": 0.14,

        "compactness_worst": 0.25,
        "worst_compactness": 0.25,

        "concavity_worst": 0.30,
        "worst_concavity": 0.30,

        "concave points_worst": 0.15,
        "worst_concave_points": 0.15,

        "symmetry_worst": 0.25,
        "worst_symmetry": 0.25,

        "fractal_dimension_worst": 0.08,
        "worst_fractal_dimension": 0.08,
    }

    return defaults.get(
        name,
        0.0
    )


def readable_feature(feature):

    return (
        str(feature)
        .replace("_", " ")
        .replace("-", " ")
        .replace("  ", " ")
        .title()
    )