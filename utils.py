import streamlit as st
import pandas as pd
import numpy as np
import shap

from pathlib import Path
from sklearn.pipeline import Pipeline






def apply_custom_css():
    """Load the shared HealthAI theme and preserve the selected theme."""
    css_path = Path(__file__).parent / "style.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    theme = st.session_state.get("healthai_theme", "light")
    marker = "healthai-theme-dark-marker" if theme == "dark" else "healthai-theme-light-marker"
    st.markdown(
        f'<div class="{marker}" aria-hidden="true" style="display:none"></div>',
        unsafe_allow_html=True,
    )


def readable_feature(feature):
    """Turn model column names into labels a normal user can understand."""
    name = str(feature).replace("_", " ").replace("-", " ")
    replacements = {
        "mean ": "Mean ",
        "se ": "SE ",
        "worst ": "Worst ",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return " ".join(name.split()).title()






def breast_default(feature):
    name = str(feature).lower().strip()
    defaults = {
        "radius_mean": 14.0,
        "mean_radius": 14.0,
        "texture_mean": 19.0,
        "mean_texture": 19.0,
        "perimeter_mean": 90.0,
        "mean_perimeter": 90.0,
        "area_mean": 650.0,
        "mean_area": 650.0,
        "smoothness_mean": 0.10,
        "mean_smoothness": 0.10,
        "compactness_mean": 0.10,
        "mean_compactness": 0.10,
        "concavity_mean": 0.09,
        "mean_concavity": 0.09,
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
    if name in defaults:
        return defaults[name]


    if "radius" in name:
        return 14.0
    if "texture" in name:
        return 19.0
    if "perimeter" in name:
        return 90.0
    if "area" in name:
        return 650.0
    if "smoothness" in name:
        return 0.10
    if "compactness" in name:
        return 0.10
    if "concavity" in name:
        return 0.09
    if "concave" in name:
        return 0.05
    if "symmetry" in name:
        return 0.18
    if "fractal" in name:
        return 0.06
    return 0.0


def get_final_model(model):
    """Return the estimator at the end of a saved sklearn Pipeline."""
    if isinstance(model, Pipeline):
        return model.steps[-1][1]
    return model


def _transform_for_shap(model, patient):
    """Transform a patient exactly as the saved pipeline does."""
    if not isinstance(model, Pipeline):
        return patient, list(patient.columns)

    transformer = model[:-1]
    transformed = patient
    if len(model.steps) > 1:
        transformed = transformer.transform(patient)

    if hasattr(transformer, "get_feature_names_out"):
        try:
            names = list(transformer.get_feature_names_out())
        except Exception:
            names = list(patient.columns)
    else:
        names = list(patient.columns)

    return transformed, names


def _normalise_shap_values(raw_values):
    """Handle SHAP list/array/Explanation output across SHAP versions."""
    values = raw_values.values if hasattr(raw_values, "values") else raw_values
    values = np.asarray(values)

    if values.ndim == 3:

        values = values[0, :, -1]
    elif values.ndim == 2:

        values = values[0]
    elif values.ndim == 1:
        values = values
    else:
        values = values.flatten()

    return np.asarray(values, dtype=float).flatten()


def _tree_shap(model, patient):
    final_model = get_final_model(model)
    transformed, feature_names = _transform_for_shap(model, patient)
    explainer = shap.TreeExplainer(final_model)

    try:
        raw = explainer(transformed)
    except Exception:
        raw = explainer.shap_values(transformed)
        if isinstance(raw, list):
            raw = raw[-1]

    values = _normalise_shap_values(raw)
    if len(values) != len(feature_names):


        if len(values) == len(patient.columns):
            feature_names = list(patient.columns)
        else:
            return None, None

    return values, [readable_feature(x) for x in feature_names]


def create_background(patient, rows=24):
    """Create a small deterministic local background for Kernel SHAP."""
    base = patient.astype(float).values[0]
    rng = np.random.default_rng(42)
    samples = []

    for _ in range(rows):
        row = base.copy()
        for i, value in enumerate(base):
            scale = max(abs(float(value)) * 0.10, 0.01)
            row[i] = float(value) + rng.normal(0, scale)
            if row[i] < 0:
                row[i] = 0.0
        samples.append(row)

    return pd.DataFrame(samples, columns=patient.columns)


def _kernel_shap(model, patient):
    background = create_background(patient)

    def predict(data):
        frame = pd.DataFrame(data, columns=patient.columns)
        if hasattr(model, "predict_proba"):
            probs = np.asarray(model.predict_proba(frame))
            return probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
        return np.asarray(model.predict(frame), dtype=float)

    explainer = shap.KernelExplainer(predict, background)
    raw = explainer.shap_values(patient, nsamples=80)
    if isinstance(raw, list):
        raw = raw[-1]
    values = _normalise_shap_values(raw)

    if len(values) != len(patient.columns):
        return None, None
    return values, [readable_feature(x) for x in patient.columns]


def generate_shap_explanation(models, patient):
    """Robust Tree-SHAP first, Kernel-SHAP fallback for all three diseases."""
    candidates = []

    if isinstance(models, dict):

        for name, model in models.items():
            if "random" in str(name).lower():
                candidates.append(model)
        for name, model in models.items():
            if "xgb" in str(name).lower() and model not in candidates:
                candidates.append(model)
        for model in models.values():
            if model not in candidates:
                candidates.append(model)
    else:
        candidates = [models]

    for model in candidates:
        try:
            values, names = _tree_shap(model, patient)
            if values is not None:
                return values, names
        except Exception:
            pass

    for model in candidates:
        try:
            values, names = _kernel_shap(model, patient)
            if values is not None:
                return values, names
        except Exception:
            pass

    return None, None






def _simple_risk_text(probability, category):
    pct = probability * 100
    if category == "Low Risk":
        meaning = "the entered information looks more similar to lower-risk examples used by the model"
    elif category == "Moderate Risk":
        meaning = "the model sees a mixed pattern, so the result is between the lower- and higher-risk groups"
    else:
        meaning = "the entered information looks more similar to higher-risk examples used by the model"

    return (
        f"The model's estimated probability is {pct:.1f}%. In simple terms, {meaning}. "
        "This is a computer-generated estimate, not a diagnosis or proof that a disease is present."
    )


def _show_plain_language_explanation(disease_name, probability, category, explanation=None):
    st.markdown('<div class="plain-language-box">', unsafe_allow_html=True)
    st.markdown("### 🧑‍⚕️ What does this mean in simple words?")
    st.write(_simple_risk_text(probability, category))

    if explanation is not None and not explanation.empty:
        top = explanation.head(5)
        names = [str(x) for x in top["Feature"].tolist()]
        st.write(
            "**What the model paid the most attention to:** "
            + ", ".join(names)
            + ". These are model signals, not medical causes."
        )

    st.caption(
        f"For {disease_name}, SHAP shows how individual inputs moved the model estimate relative to its baseline."
    )
    st.markdown('</div>', unsafe_allow_html=True)






def display_shap(models, patient, disease_name, probability=None, category=None, show_simple=True):
    st.subheader("🔎 Explainable AI")

    values, names = generate_shap_explanation(models, patient)

    if values is None:
        st.info(
            "The prediction was generated, but a case-level SHAP explanation "
            "could not be calculated for this saved model."
        )
        return

    explanation = pd.DataFrame(
        {
            "Feature": names,
            "SHAP Impact": values,
            "Absolute Impact": np.abs(values),
        }
    ).sort_values("Absolute Impact", ascending=False)

    top = explanation.head(10).copy()
    top["Direction"] = np.where(
        top["SHAP Impact"] >= 0,
        "Pushes estimate higher",
        "Pushes estimate lower",
    )
    top["SHAP Impact"] = top["SHAP Impact"].map(lambda x: f"{x:.4f}")

    if show_simple and probability is not None and category is not None:
        _show_plain_language_explanation(
            disease_name, probability, category, explanation
        )

    st.markdown(
        f"**Top factors the {disease_name} model considered:**"
    )
    st.dataframe(
        top[["Feature", "SHAP Impact", "Direction"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📌 SHAP Feature Contribution")
    chart = (
        explanation.head(10)
        .sort_values("SHAP Impact")
        .set_index("Feature")[["SHAP Impact"]]
    )
    st.bar_chart(chart, use_container_width=True)
    st.caption(
        "Positive values push the model estimate toward higher risk; negative values push it toward lower risk. "
        "SHAP values describe model behaviour, not medical causation."
    )






def display_prediction(models, patient, disease_name):
    st.divider()
    st.subheader("📊 Risk Assessment")

    predictions = []
    model_results = {}

    if isinstance(models, dict):
        for model_name, model in models.items():
            try:
                if hasattr(model, "predict_proba"):
                    probability = float(model.predict_proba(patient)[0][1])
                    prediction = model.predict(patient)[0]
                else:
                    prediction = model.predict(patient)[0]
                    probability = float(prediction)

                predictions.append(probability)
                model_results[str(model_name)] = {
                    "prediction": prediction,
                    "probability": probability,
                }
            except Exception as exc:
                st.warning(f"Could not generate prediction from {model_name}: {exc}")
    else:
        try:
            if hasattr(models, "predict_proba"):
                probability = float(models.predict_proba(patient)[0][1])
                prediction = models.predict(patient)[0]
            else:
                prediction = models.predict(patient)[0]
                probability = float(prediction)

            predictions.append(probability)
            model_results["Model"] = {
                "prediction": prediction,
                "probability": probability,
            }
        except Exception as exc:
            st.error(f"Prediction failed: {exc}")
            return

    if not predictions:
        st.error("No model prediction could be generated.")
        return

    overall_probability = float(np.mean(predictions))
    risk_percentage = overall_probability * 100

    if overall_probability < 0.30:
        risk_category = "Low Risk"
    elif overall_probability < 0.70:
        risk_category = "Moderate Risk"
    else:
        risk_category = "High Risk"

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Estimated Risk", f"{risk_percentage:.2f}%")
    with col2:
        st.metric("Risk Category", risk_category)

    st.progress(min(max(overall_probability, 0.0), 1.0))


    _show_plain_language_explanation(disease_name, overall_probability, risk_category)

    st.subheader("🤖 Model Predictions")
    rows = []
    for model_name, result in model_results.items():
        try:
            prediction_text = "Higher Risk" if int(result["prediction"]) == 1 else "Lower Risk"
        except Exception:
            prediction_text = str(result["prediction"])
        rows.append(
            {
                "Model": model_name,
                "Prediction": prediction_text,
                "Risk Probability": f"{result['probability'] * 100:.2f}%",
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.info(
        "The overall estimate is the average probability produced by the available trained models. "
        "A probability is not a diagnosis."
    )


    display_shap(
        models,
        patient,
        disease_name,
        probability=overall_probability,
        category=risk_category,
        show_simple=False,
    )

    st.caption(
        f"{disease_name} assessment generated using the trained machine-learning model(s)."
    )
    st.warning(
        "This application is a research/academic prototype and is not a medical diagnosis."
    )
    return {
        "probability": overall_probability,
        "risk_category": risk_category,
        "evaluation": (
            f"The model estimated an overall risk of "
            f"{risk_percentage:.2f}% and classified the result as "
            f"{risk_category}."
        ),
    }


def apply_common_style():
    """Compatibility wrapper used by older disease pages."""
    apply_custom_css()
