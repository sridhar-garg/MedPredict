"""Reviews and explicitly illustrative experience content."""
import streamlit as st
st.set_page_config(page_title="Reviews | MedPredict", page_icon="assets/favicon.svg", layout="wide", initial_sidebar_state="auto")
from sidebar_compat import show_sidebar
from utils import apply_custom_css
show_sidebar()
apply_custom_css()
from reviews_content import render_reviews
render_reviews()
