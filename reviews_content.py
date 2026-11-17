"""Clearly labelled placeholder feedback; replace only with supplied real results."""
import streamlit as st

DEMO_REVIEWS = [
    {"name": "Demo reviewer 01", "context": "Sample interface walkthrough", "rating": 5,
     "title": "A clear place to start", "comment": "The assessment choices are easy to find, and the next step is clear."},
    {"name": "Demo reviewer 02", "context": "Sample readability check", "rating": 4,
     "title": "Explanations in plain language", "comment": "The explanations make the model output easier to follow. A glossary would make unfamiliar terms even clearer."},
    {"name": "Demo reviewer 03", "context": "Sample navigation check", "rating": 5,
     "title": "Everything feels connected", "comment": "Moving between assessments, reports and the help tools feels straightforward."},
]


def render_reviews():
    st.title("Reviews & experience")
    st.caption("A space for feedback on the MedPredict experience.")
    st.info("DEMO CONTENT — All ratings, reviewers and comments below are fictional placeholders. "
            "They are not verified user feedback, clinical evidence or results from real assessments.")

    review_tab, usage_tab = st.tabs(["Reviews", "Real-life usage"])
    with review_tab:
        rating = sum(item["rating"] for item in DEMO_REVIEWS) / len(DEMO_REVIEWS)
        a, b, c = st.columns(3)
        a.metric("Illustrative rating", f"{rating:.1f} / 5")
        b.metric("Placeholder reviews", str(len(DEMO_REVIEWS)))
        c.metric("Verified feedback", "Not added")
        st.subheader("Sample first impressions")
        st.caption("These examples describe interface usability only. They do not describe health outcomes.")
        for item in DEMO_REVIEWS:
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['name']} · {item['context']}")
                with right:
                    st.markdown(f"**{item['rating']} / 5** · Demo")
                st.write(item["comment"])
        st.caption("Real feedback can replace these examples after assessment trials.")

    with usage_tab:
        st.subheader("Real-world evidence, when it is available")
        st.write("No verified usage statistics or real assessment outcomes have been added yet.")
        for title, copy in [
            ("Usability observations", "Navigation, readability and the steps people found easy or difficult."),
            ("Assessment experience", "What participants reported about completing an assessment and understanding its explanation."),
            ("Verified results", "Actual study details and results can be added after a real evaluation; none are claimed here."),
        ]:
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(copy)
        st.caption("Any future findings should distinguish interface feedback from clinical performance.")
