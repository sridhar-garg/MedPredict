"""Personal dashboard cards and charts backed by saved account records."""

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from html import escape
import logging
from math import isfinite
from zoneinfo import ZoneInfo

import altair as alt
import streamlit as st

from database import get_dashboard_records
from ui import html, icon


ASSESSMENTS = {
    "diabetes": ("Diabetes", "pages/diabetes_app.py", "drop", "blue"),
    "heart disease": ("Heart health", "pages/heart_app.py", "heart", "coral"),
    "breast cancer": ("Breast cancer", "pages/breast_app.py", "ribbon", "rose"),
}
ACTIVITY_TYPES = {
    "Assessments": ("Completed assessments", "Assessment", "blue", "pulse"),
    "Screenings": ("Completed screenings", "Screening", "teal", "shield"),
    "Reports": ("Saved report readings", "Report reading", "violet", "book"),
    "Imaging": ("Saved imaging analyses", "Imaging analysis", "amber", "scan"),
}
CHART_COLORS = {
    "blue": ("#2569b3", "#80b9f4"),
    "coral": ("#b84b32", "#fbab8c"),
    "rose": ("#b04477", "#ef9cc4"),
    "teal": ("#168472", "#6ed9c0"),
    "violet": ("#7352b5", "#c3adfc"),
    "amber": ("#a46b15", "#edbe62"),
}
WATCH_THRESHOLD = 0.60
LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _saved_at(value):
    try:
        timestamp = datetime.fromisoformat(str(value))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(LOCAL_TIMEZONE)
    except (ValueError, OverflowError):
        return None


def _date(record):
    return record["saved_at"].strftime("%d %b %Y") if record["saved_at"] else "Date unavailable"


def _probability(value):
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return score if isfinite(score) and 0 <= score <= 1 else None


def _score(score):
    return f"{score:.2%}" if score is not None else "Estimate unavailable"


def _heading(title, glyph, tone, level=3):
    html(f'<div class="mp-tracking-heading"><span class="mp-tracking-icon mp-{tone}">{icon(glyph, 21)}</span>'
         f'<h{level}>{escape(title)}</h{level}></div>')


def _empty(title, description):
    html(f'<div class="mp-tracking-empty"><strong>{escape(title)}</strong><p>{escape(description)}</p></div>')


def _counts(assessments, work):
    counts = Counter(entry["kind"] for entry in work)
    counts["Assessments"] = len(assessments)
    cards = "".join(
        f'<li data-tone="{tone}"><span class="mp-tracking-icon mp-{tone}">{icon(glyph, 23)}</span>'
        f'<div><b>{counts[kind]:,}</b><span>{label}</span></div></li>'
        for kind, (label, _, tone, glyph) in ACTIVITY_TYPES.items()
    )
    html(f'<ul class="mp-tracking-counts" aria-label="Lifetime activity totals">{cards}</ul>')


def _latest_cards(by_disease):
    st.subheader("Your latest assessments")
    for column, (key, (name, page, glyph, tone)) in zip(st.columns(3), ASSESSMENTS.items()):
        with column, st.container(border=True, key=f"tracking_latest_{tone}"):
            _heading(name, glyph, tone)
            records = by_disease.get(key)
            if not records:
                _empty("No saved result yet", "Complete an assessment to see your estimate here.")
                st.page_link(page, label="Start assessment", icon=":material/arrow_forward:")
                continue
            latest = records[0]
            score = latest["probability"]
            if score is None:
                _empty("Estimate unavailable", "Open the saved result for details.")
            else:
                html(
                    f'<div class="mp-tracking-estimate">'
                    f'<div class="mp-tracking-ring" style="--mp-score:{score:.6%}"><b>{_score(score)}</b></div>'
                    f'<div><strong>Latest model estimate</strong><small>Saved {_date(latest)}</small></div>'
                    '</div>'
                )
            st.page_link("pages/history.py", label="View result", icon=":material/arrow_forward:",
                         query_params={"assessment": str(latest["id"])})


def _watch_card(by_disease, names):
    _heading("Assessment watch", "shield", "amber")
    st.caption("Conditions with any saved estimate above 60%. Each entry shows the most recent result.")
    watched = []
    for condition, records in by_disease.items():
        highs = [record for record in records
                 if record["probability"] is not None and record["probability"] > WATCH_THRESHOLD]
        if highs:
            watched.append((condition, records, max(highs, key=lambda record: record["probability"])))
    watched.sort(key=lambda item: (item[1][0]["probability"] or 0) > WATCH_THRESHOLD, reverse=True)
    if not watched:
        _empty("No estimates above 60%", "Saved results that cross the watch threshold will appear here.")
        return

    rows = []
    for condition, records, peak in watched:
        latest = records[0]
        score = latest["probability"]
        status = "Latest above 60%" if score is not None and score > WATCH_THRESHOLD else "Earlier result above 60%"
        comparison = "First saved assessment"
        if len(records) > 1:
            prior = records[1]
            comparison = f"Previous {_score(prior['probability'])} · {_date(prior)}"
            if score is not None and prior["probability"] is not None:
                points = round((score - prior["probability"]) * 100, 2)
                comparison += f" · {points:+.2f} percentage points" if points else " · No change"
        rows.append(
            '<li><div class="mp-watch-head">'
            f'<strong>{escape(names[condition])}</strong><b>{_score(score)}</b></div>'
            f'<div class="mp-watch-meta"><span>{status}</span><time>Latest · {_date(latest)}</time></div>'
            f'<small>{escape(comparison)}</small><small>Highest saved {_score(peak["probability"])} · {_date(peak)}</small></li>'
        )
    html(f'<ul class="mp-watch-list">{"".join(rows)}</ul>')


def _chart_color(tone):
    return CHART_COLORS[tone][st.session_state.get("healthai_theme") == "dark"]


def _chart(chart, label, key):
    dark = st.session_state.get("healthai_theme") == "dark"
    text, grid = ("#c6dbe6", "#38545f") if dark else ("#405c6a", "#dfe9ec")
    styled = (
        chart.properties(height=190, background="transparent")
        .configure_view(stroke=None)
        .configure_axis(labelColor=text, titleColor=text, gridColor=grid, tickColor=grid,
                        domain=False, labelFont="sans-serif", titleFont="sans-serif",
                        labelFontSize=12, titlePadding=12)
    )
    st.altair_chart(styled, width="stretch", theme=None, key=key, alt=label)


def _estimate_chart(by_disease, names):
    _heading("Model estimate history", "pulse", "blue")
    available = [condition for condition, records in by_disease.items()
                 if any(record["probability"] is not None for record in records)]
    if not available:
        _empty("Your trend starts here", "Saved model estimates will appear on this graph.")
        return
    condition = st.selectbox("Assessment", available, format_func=names.get, key="tracking_estimate_condition")
    tone = ASSESSMENTS.get(condition, (None, None, None, "violet"))[3]
    color = _chart_color(tone)
    valid = [record for record in reversed(by_disease[condition]) if record["probability"] is not None]
    source = alt.InlineData(values=[
        {"number": number, "estimate": record["probability"], "saved": _date(record)}
        for number, record in enumerate(valid, 1)
    ])
    base = alt.Chart(source).encode(
        x=alt.X("number:Q", title="Saved estimate", scale=alt.Scale(domain=[0.5, len(valid) + 0.5]),
                axis=alt.Axis(tickMinStep=1, format="d", grid=False)),
        y=alt.Y("estimate:Q", title="Model estimate", scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format=".0%", tickCount=5)),
    )
    area = base.mark_area(color=color, opacity=0.12)
    threshold = alt.Chart(alt.InlineData(values=[{"estimate": WATCH_THRESHOLD}])).mark_rule(
        color=_chart_color("amber"), strokeDash=[5, 5], strokeWidth=1.5,
    ).encode(y=alt.Y("estimate:Q"))
    line = base.mark_line(color=color, strokeWidth=3)
    points = base.mark_circle(color=color, size=85, opacity=1).encode(tooltip=[
        alt.Tooltip("number:Q", title="Saved estimate"),
        alt.Tooltip("saved:N", title="Date"),
        alt.Tooltip("estimate:Q", title="Model estimate", format=".2%"),
    ])
    _chart(area + threshold + line + points, f"Saved {names[condition]} model estimates in order",
           "tracking_estimate_chart")
    st.caption("Each point is a model estimate for the inputs saved with that assessment. The dashed line marks 60%.")


def _monthly_activity(entries):
    now = datetime.now(LOCAL_TIMEZONE)
    current = now.year * 12 + now.month - 1
    months = [date(index // 12, index % 12 + 1, 1) for index in range(current - 5, current + 1)]
    counts = Counter(
        (entry["saved_at"].year, entry["saved_at"].month, entry["kind"])
        for entry in entries if entry["saved_at"]
    )
    present_kinds = {entry["kind"] for entry in entries}
    kinds = [kind for kind in ACTIVITY_TYPES if kind in present_kinds]
    rows = [
        {"month": month.strftime("%b %y"), "kind": kind, "count": counts[(month.year, month.month, kind)]}
        for month in months for kind in kinds
    ]
    if not any(row["count"] for row in rows):
        _empty("No activity in this period", "Items saved in the last six calendar months will appear here.")
        return
    bars = alt.Chart(alt.InlineData(values=rows)).mark_bar(size=23).encode(
        x=alt.X("month:N", title=None, sort=[month.strftime("%b %y") for month in months],
                axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("count:Q", title="Saved items", axis=alt.Axis(tickMinStep=1, format="d")),
        color=alt.Color("kind:N", legend=None,
                        scale=alt.Scale(domain=kinds,
                                        range=[_chart_color(ACTIVITY_TYPES[kind][2]) for kind in kinds])),
        tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("kind:N", title="Type"),
                 alt.Tooltip("count:Q", title="Saved items")],
    )
    _chart(bars, "Saved health activity by month and type", "tracking_monthly_chart")
    legend = "".join(
        f'<li style="--mp-chart-color:{_chart_color(ACTIVITY_TYPES[kind][2])}"><i></i>{kind}</li>'
        for kind in kinds
    )
    html(f'<ul class="mp-activity-legend" aria-label="Activity chart legend">{legend}</ul>')


def _recent_activity(entries):
    with st.container(border=True, key="tracking_recent"):
        _heading("Recent activity", "history", "teal")
        selected = st.selectbox("Filter activity", ["All activity", *ACTIVITY_TYPES],
                                key="dashboard_activity_filter")
        matching = [entry for entry in entries if selected == "All activity" or entry["kind"] == selected]
        graph, timeline = st.columns(2, gap="large")
        with graph:
            st.markdown("#### Last six months")
            _monthly_activity(matching)
        with timeline:
            st.markdown("#### Latest records")
            if matching:
                items = "".join(
                    f'<li data-tone="{ACTIVITY_TYPES[entry["kind"]][2]}">'
                    f'<div><b>{escape(entry["title"])}</b><small>{ACTIVITY_TYPES[entry["kind"]][1]}</small></div>'
                    f'<time>{_date(entry)}</time></li>'
                    for entry in matching[:5]
                )
                html(f'<ol class="mp-activity-timeline">{items}</ol>')
            else:
                _empty("No saved records in this view", "Assessments, screenings, reports, and imaging will appear as you save them.")
            st.page_link("pages/history.py", label="Full history", icon=":material/history:")


def render_dashboard_activity(user_id):
    with st.container(key="mp_dashboard_activity"):
        _heading("Your health activity", "pulse", "teal", level=2)
        try:
            assessments, work = get_dashboard_records(user_id)
        except Exception:
            logging.getLogger(__name__).warning("Dashboard activity could not be loaded")
            st.warning("Your saved activity is temporarily unavailable.")
            return

        by_disease = defaultdict(list)
        names = {key: details[0] for key, details in ASSESSMENTS.items()}
        entries = []
        for record in assessments:
            disease = record["disease"].strip()
            key = disease.casefold()
            names.setdefault(key, disease)
            record["probability"] = _probability(record["probability"])
            record["saved_at"] = _saved_at(record["created_at"])
            by_disease[key].append(record)
            entries.append(dict(kind="Assessments", title=names[key], saved_at=record["saved_at"]))
        for entry in work:
            entries.append(dict(entry, saved_at=_saved_at(entry["created_at"])))
        entries.sort(key=lambda entry: entry["saved_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        _counts(assessments, work)
        _latest_cards(by_disease)
        watch, estimate = st.columns([1, 1.15], gap="medium")
        with watch, st.container(border=True, key="tracking_watch"):
            _watch_card(by_disease, names)
        with estimate, st.container(border=True, key="tracking_trend"):
            _estimate_chart(by_disease, names)
        _recent_activity(entries)
