"""Educational screening calculations for MedPredict.

No result here is a diagnosis, a calibrated probability, or medical advice.
Only use with appropriately measured adult inputs.
"""

from __future__ import annotations

import re
from typing import Dict, Optional


SOURCES = {
    "blood_pressure": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings",
    "kidney": "https://www.kidney.org/ckd-epi-creatinine-equation-2021",
    "anaemia": "https://www.who.int/publications-detail-redirect/9789240088542",
    "bmi": "https://www.who.int/news-room/fact-sheets/detail/obesity-and-overweight",
    "liver": "https://www.aasld.org/liver-fellow-network/core-series/clinical-pearls/spare-me-jab-noninvasive-assessment-patients-masld",
    "sleep": "https://www.stopbang.ca/osa/screening.php",
    "cholesterol": "https://medlineplus.gov/ldlthebadcholesterol.html",
}


def assess_bp(systolic: float, diastolic: float) -> dict:
    if not (40 <= systolic <= 300 and 20 <= diastolic <= 200):
        raise ValueError("Enter plausible blood-pressure readings in mmHg.")
    if systolic > 180 or diastolic > 120:
        return {"label": "Severely elevated reading", "level": "error", "detail":
                "Recheck correctly. Seek urgent medical guidance; chest pain, weakness, trouble breathing, severe headache or other concerning symptoms require emergency care."}
    if systolic >= 140 or diastolic >= 90:
        return {"label": "Stage 2 range", "level": "warning", "detail":
                "A single reading cannot diagnose hypertension. Confirm with appropriately repeated measurements and a clinician."}
    if systolic >= 130 or diastolic >= 80:
        return {"label": "Stage 1 range", "level": "warning", "detail":
                "Confirm with appropriately repeated measurements and discuss with a clinician."}
    if systolic >= 120 and diastolic < 80:
        return {"label": "Elevated range", "level": "info", "detail":
                "This reading is elevated; monitor readings with appropriate technique."}
    return {"label": "Normal range", "level": "success", "detail":
            "This one reading is within the standard adult category; it does not exclude future hypertension."}


def egfr_2021(age: int, creatinine_mg_dl: float, sex_for_equation: str) -> float:
    """NKF 2021 CKD-EPI creatinine eGFR for adults, mL/min/1.73m²."""
    if age < 18 or age > 120 or creatinine_mg_dl <= 0:
        raise ValueError("eGFR calculation requires adult age and positive serum creatinine.")
    if sex_for_equation not in ("Female", "Male"):
        raise ValueError("Select the lab's sex coefficient for the equation.")
    female = sex_for_equation == "Female"
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    ratio = creatinine_mg_dl / kappa
    return (142 * min(ratio, 1) ** alpha * max(ratio, 1) ** -1.200
            * 0.9938 ** age * (1.012 if female else 1))


def assess_egfr(value: float) -> dict:
    if value < 15:
        return {"label": "Very severely reduced estimated filtration", "level": "error", "detail":
                "A result this low merits prompt professional evaluation. Kidney failure cannot be diagnosed by this number alone."}
    if value < 30:
        return {"label": "Severely reduced estimated filtration", "level": "warning", "detail":
                "Discuss with a clinician promptly. Repeat tests and other evidence are required."}
    if value < 60:
        return {"label": "Reduced estimated filtration", "level": "warning", "detail":
                "CKD generally requires an abnormality lasting at least 3 months or other evidence of kidney damage."}
    return {"label": "eGFR of 60 or higher", "level": "info", "detail":
            "Kidney disease can still occur with normal eGFR. Urine albumin and medical history are also important."}


def assess_haemoglobin(hb_g_dl: float, group: str) -> dict:
    """Simplified WHO 2024 adult 15–65-year thresholds; nonpregnant groups only."""
    if hb_g_dl <= 0 or hb_g_dl > 25:
        raise ValueError("Enter a plausible haemoglobin value in g/dL.")
    if group not in ("Non-pregnant woman", "Man"):
        raise ValueError("Select one of the two supported nonpregnant adult groups.")
    cutoff = 12 if group == "Non-pregnant woman" else 13
    if hb_g_dl < 8:
        return {"label": "Severe anaemia range", "level": "error", "detail":
                "Needs prompt clinical review. Haemoglobin alone does not determine the underlying cause."}
    if hb_g_dl < 11:
        return {"label": "Moderate anaemia range", "level": "warning", "detail":
                "Clinical assessment and further tests can help identify the cause."}
    if hb_g_dl < cutoff:
        return {"label": "Mild anaemia range", "level": "warning", "detail":
                "Clinical interpretation depends on age, pregnancy, altitude and other factors."}
    return {"label": "Above selected anaemia cutoff", "level": "info", "detail":
            "Other blood disorders remain possible; interpret with full blood count and symptoms."}


def assess_ldl(ldl_mg_dl: float) -> dict:
    if ldl_mg_dl < 0 or ldl_mg_dl > 500:
        raise ValueError("Enter a plausible LDL value in mg/dL.")
    if ldl_mg_dl >= 190:
        return {"label": "Very high LDL level", "level": "warning", "detail":
                "Seek professional evaluation. LDL targets depend on cardiovascular risk and treatment history."}
    if ldl_mg_dl >= 160:
        cat = "High LDL level"
    elif ldl_mg_dl >= 130:
        cat = "Borderline-high LDL level"
    elif ldl_mg_dl >= 100:
        cat = "Near-optimal LDL level"
    else:
        cat = "Below 100 mg/dL"
    return {"label": cat, "level": "info", "detail":
            "This is a conventional LDL category, not a diagnosis or personalised treatment target."}


def assess_bmi(height_cm: float, weight_kg: float) -> tuple[float, dict]:
    if not 90 <= height_cm <= 250 or not 10 <= weight_kg <= 450:
        raise ValueError("Enter plausible height and weight values.")
    bmi = weight_kg / (height_cm / 100) ** 2
    if bmi >= 30:
        label = "Obesity-range BMI"
    elif bmi >= 25:
        label = "Overweight-range BMI"
    elif bmi >= 18.5:
        label = "Standard-range BMI"
    else:
        label = "Underweight-range BMI"
    return bmi, {"label": label, "level": "info", "detail":
                 "BMI is an adult population screening index. It does not measure body fat or diagnose metabolic disease. Asian populations may have increased risks at lower BMI."}


def assess_stop_bang(flags: list[bool]) -> tuple[int, dict]:
    if len(flags) != 8:
        raise ValueError("STOP-BANG requires eight yes/no items.")
    score = sum(bool(x) for x in flags)
    if score >= 5:
        label = "High screening risk of obstructive sleep apnoea"
    elif score >= 3:
        label = "Intermediate screening risk of obstructive sleep apnoea"
    else:
        label = "Lower screening risk of obstructive sleep apnoea"
    return score, {"label": label, "level": "info", "detail":
                   "A STOP-BANG result is a screening score, not a diagnosis. Only appropriate clinical testing can establish sleep apnoea."}


def fib4(age: int, ast: float, alt: float, platelets_10_9_l: float) -> float:
    if age < 18 or age > 120 or min(ast, alt, platelets_10_9_l) <= 0:
        raise ValueError("Use adult age and positive AST, ALT, and platelet measurements.")
    return (age * ast) / (platelets_10_9_l * alt ** 0.5)


def assess_fib4(age: int, value: float) -> dict:
    if age < 35:
        return {"label": "FIB-4 not reliable in this age group", "level": "info", "detail":
                "This score is poorly reliable under 35. Specialist evaluation may be needed if there is clinical concern."}
    low = 2.0 if age >= 65 else 1.3
    if value > 2.67:
        return {"label": "Higher screening risk of advanced liver fibrosis", "level": "warning", "detail":
                "Needs a clinician's interpretation and confirmatory testing. FIB-4 is not a liver disease diagnosis."}
    if value >= low:
        return {"label": "Indeterminate range; further assessment suggested", "level": "warning", "detail":
                "Usually requires follow-up testing such as elastography when clinically appropriate."}
    return {"label": "Lower screening risk of advanced liver fibrosis", "level": "info", "detail":
            "A low FIB-4 does not rule out other liver disease; this score was designed for defined clinical populations."}



REPORT_PATTERNS = {
    "Haemoglobin (g/dL)": r"\b(?:ha?emoglobin|hb)\b[^\n\d]{0,35}(\d{1,2}(?:\.\d{1,2})?)\s*(?:g\s*/\s*d[lL])?\b",
    "Creatinine (mg/dL)": r"\b(?:serum\s+)?creatinine\b[^\n\d]{0,35}(\d{1,2}(?:\.\d{1,2})?)\s*(?:mg\s*/\s*d[lL])?\b",
    "LDL (mg/dL)": r"\b(?:LDL(?:[- ]cholesterol)?|low density lipoprotein)\b[^\n\d]{0,35}(\d{1,3}(?:\.\d{1,2})?)\s*(?:mg\s*/\s*d[lL])?\b",
    "AST (U/L)": r"\b(?:AST|SGOT)\b[^\n\d]{0,35}(\d{1,3}(?:\.\d{1,2})?)\b",
    "ALT (U/L)": r"\b(?:ALT|SGPT)\b[^\n\d]{0,35}(\d{1,3}(?:\.\d{1,2})?)\b",
    "Platelets (10^9/L)": r"\b(?:platelets?|platelet\s+count)\b[^\n\d]{0,35}(\d{2,3}(?:\.\d{1,2})?)\b",
}


def extract_candidate_lab_values(text: str) -> Dict[str, float]:
    """Best-effort extraction; all values and units require manual verification."""
    result = {}
    for label, pattern in REPORT_PATTERNS.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                result[label] = float(match.group(1))
            except ValueError:
                pass
    return result
