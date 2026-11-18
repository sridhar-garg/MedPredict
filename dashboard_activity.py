"""Account activity summaries for the signed-in dashboard."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
import logging
from math import isfinite
from zoneinfo import ZoneInfo

import streamlit as st

from database import get_dashboard_records
from ui import html, icon


ASSESSMENTS = (
    ("diabetes", "Diabetes", "pages/diabetes_app.py", "drop", "blue"),
    ("heart disease", "Heart health", "pages/heart_app.py", "heart", "coral"),
    ("breast cancer", "Breast cancer", "pages/breast_app.py", "ribbon", "rose"),
)
ACTIVITY_LABELS = {
    "Assessments": ("Completed assessments", "Assessment"),
    "Screenings": ("Completed screenings", "Screening"),
    "Reports": ("Saved report readings", "Report reading"),
    "Imaging": ("Saved imaging analyses", "Imaging analysis"),
}
WATCH_THRESHOLD = 0.60
LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _time(value):
    try:
        result = datetime.fromisoformat(str(value))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _date(record):
    saved_at = _time(record["created_at"])
    return saved_at.astimezone(LOCAL_TIMEZONE).strftime("%d %b %Y") if saved_at else "Date unavailable"


def _probability(value):
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return score if isfinite(score) and 0 <= score <= 1 else None


def _score(score):
    return f"{score:.2%}" if score is not None else "Estimate unavailable"


def _latest_cards(by_disease):
    st.subheader("Your latest assessments")
    for column, (key, name, page, glyph, tone) in zip(st.columns(3), ASSESSMENTS):
        with column, st.container(border=True, key=f"dashboard_latest_{tone}"):
            html(f'<div class="mp-tracking-label"><span class="mp-icon mp-{tone}">{icon(glyph, 20)}</span>'
                 f'<h3>{name}</h3></div>')
            records = by_disease.get(key)
            if records:
                latest = records[0]
                st.metric("Latest model estimate", _score(latest["probability"]))
                st.caption(f"Saved {_date(latest)}")
                st.page_link("pages/history.py", label="View result", icon=":material/arrow_forward:",
                             query_params={"assessment": str(latest["id"])})
            else:
                st.caption("No saved assessment yet.")
                st.page_link(page, label="Start assessment", icon=":material/arrow_forward:")


def _watch_card(by_disease):
    names = {key: name for key, name, *_ in ASSESSMENTS}
    above_threshold = []
    for key, records in by_disease.items():
        past_highs = [record for record in records
                      if record["probability"] is not None and record["probability"] > WATCH_THRESHOLD]
        if past_highs:
            above_threshold.append((names.get(key, records[0]["disease"]), records, past_highs))

    # Group conditions currently above the threshold before historical ones.
    above_threshold.sort(
        key=lambda item: (item[1][0]["probability"] or 0) > WATCH_THRESHOLD,
        reverse=True,
    )
    with st.container(border=True, key="dashboard_watch"):
        st.subheader("Assessment watch")
        st.caption("Conditions with any saved model estimate above 60%. Each row shows the latest result for that condition.")
        if not above_threshold:
            st.write("No saved model estimates above 60% yet.")
            return

        for name, records, past_highs in above_threshold:
            latest = records[0]
            score = latest["probability"]
            peak = max(past_highs, key=lambda record: record["probability"])
            prior = records[1] if len(records) > 1 else None
            comparison = "No earlier assessment"
            if prior:
                previous_score = prior["probability"]
                comparison = f"Previous {_score(previous_score)} · {_date(prior)}"
                if score is not None and previous_score is not None:
                    points = (score - previous_score) * 100
                    comparison += f" · {points:+.2f} percentage points" if round(points, 2) else " · No change"
            status = "Latest above 60%" if score is not None and score > WATCH_THRESHOLD else "Earlier result above 60%"
            html(
                '<div class="mp-watch-entry">'
                f'<div><h3>{escape(name)}</h3><span class="mp-watch-status">{status}</span></div>'
                f'<div><b>{_score(score)}</b><small>Latest · {_date(latest)}</small></div>'
                f'<div><span>{escape(comparison)}</span>'
                f'<small>Highest saved {_score(peak["probability"])} · {_date(peak)}</small></div>'
                '</div>'
            )
        st.caption("These are model estimates based on the information entered. A change in score alone cannot establish a change in your health.")


def _recent_activity(assessments, work):
    names = {key: name for key, name, *_ in ASSESSMENTS}
    entries = [
        dict(kind="Assessments", title=names.get(row["disease"].casefold(), row["disease"]),
             created_at=row["created_at"])
        for row in assessments
    ] + work
    entries.sort(key=lambda entry: _time(entry["created_at"]) or datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True)
    with st.container(border=True, key="dashboard_recent"):
        st.subheader("Recent activity")
        selected = st.selectbox("Filter activity", ["All activity", *ACTIVITY_LABELS],
                                key="dashboard_activity_filter")
        recent = [entry for entry in entries if selected == "All activity" or entry["kind"] == selected][:5]
        if recent:
            items = "".join(
                f'<li><div><b>{escape(entry["title"])}</b><small>{ACTIVITY_LABELS[entry["kind"]][1]}</small></div>'
                f'<time>{_date(entry)}</time></li>'
                for entry in recent
            )
            html(f'<ol class="mp-activity-timeline">{items}</ol>')
        else:
            st.caption("No saved activity in this view yet.")
        st.page_link("pages/history.py", label="Full history", icon=":material/history:")


def render_dashboard_activity(user_id):
    try:
        assessments, work = get_dashboard_records(user_id)
    except Exception:
        logging.getLogger(__name__).warning("Dashboard activity could not be loaded")
        st.warning("Your saved activity is temporarily unavailable.")
        return

    by_disease = defaultdict(list)
    for record in assessments:
        record["disease"] = record["disease"].strip()
        record["probability"] = _probability(record["probability"])
        by_disease[record["disease"].casefold()].append(record)

    counts = Counter(item["kind"] for item in work)
    counts["Assessments"] = len(assessments)
    st.subheader("Your activity at a glance")
    with st.container(key="dashboard_counts"):
        for column, (kind, (label, _)) in zip(st.columns(4, gap="small"), ACTIVITY_LABELS.items()):
            column.metric(label, f"{counts[kind]:,}")
    _latest_cards(by_disease)
    _watch_card(by_disease)
    _recent_activity(assessments, work)
