"""MedPredict X Disease Atlas, grounded in NLM MedlinePlus topics."""
from __future__ import annotations
import streamlit as st
from disease_information import lookup_topics,atlas_queries

st.set_page_config(page_title="Disease Atlas | MedPredict X",page_icon="📚",layout="wide")


from sidebar_compat import show_sidebar
show_sidebar()
try:
    from utils import apply_custom_css
    apply_custom_css()
except (ImportError,AttributeError):pass
if not st.session_state.get('is_logged_in',False):
    st.warning('Sign in to explore Disease Atlas.')
    st.page_link('app.py',label='Go to sign in',icon='🏠')
    st.stop()

st.title('📚 Disease Atlas')
st.caption('Search health conditions · Learn prevention · Understand treatment and symptom management')
st.info('Information is retrieved from the U.S. National Library of Medicine (MedlinePlus). '
        'It is educational, not a diagnosis or a personalised treatment plan. '
        'Some diseases cannot be prevented or cured, and not every rare disease is indexed.')

@st.cache_data(ttl=24*3600,show_spinner=False)
def cached_lookup(term:str,max_results:int=5):return lookup_topics(term,max_results)

with st.form('atlas_search'):
    query=st.text_input('Search for a disease or condition',placeholder='e.g., asthma, dengue, type 2 diabetes, migraine',max_chars=100)
    search=st.form_submit_button('Search reliable medical sources',type='primary')
if search:st.session_state['mp_atlas_query']=query.strip()
term=st.session_state.get('mp_atlas_query','')
if not term:
    st.caption('Enter a condition to begin. No diagnosis or private medical records are required.')
    st.stop()

try:
    with st.spinner('Searching MedlinePlus…'):
        results=cached_lookup(term,6)
except Exception as e:
    st.error('The trusted health-information service could not be reached. Please try again later.')
    st.caption(f'Service detail: {type(e).__name__}')
    st.link_button('Open MedlinePlus directly','https://medlineplus.gov/healthtopics.html')
    st.stop()
if not results:
    st.warning('No MedlinePlus entry matched this search. Try another spelling, the medical name, or a broader topic.')
    st.stop()

names=[f'{topic.title} — {topic.url.split("/")[-1]}' for topic in results]
selected=st.selectbox('Matching topics',range(len(results)),format_func=lambda idx:names[idx])
topic=results[selected]
st.subheader(topic.title)
st.write(topic.summary if topic.summary else 'Read the linked MedlinePlus article for the complete overview.')
st.link_button('Read full verified MedlinePlus article ↗',topic.url)

mode=st.radio('What would you like to understand?',
              ['I do not have this condition','I have this condition or care for someone who does'],
              horizontal=True)
keyword,heading=atlas_queries(topic.title,'prevent' if mode.startswith('I do not') else 'manage')
st.subheader(heading)
st.caption('Related health-education articles from the National Library of Medicine, not automatically generated treatment instructions.')
try:
    with st.spinner('Finding related guidance…'):
        guides=cached_lookup(keyword,5)
    if not guides:
        st.warning('No specific MedlinePlus guidance was returned for this topic. Read the original article and consult a healthcare professional.')
    for item in guides:
        with st.expander(item.title,expanded=item.url==topic.url):
            if item.summary:st.write(item.summary[:2300])
            st.link_button('Read source ↗',item.url)
except Exception:
    st.warning('Related guidance is temporarily unavailable. Use the primary article above.')

if mode.startswith('I do not'):
    st.caption('Prevention may not be possible for every condition. Distinguish evidence-based risk reduction from guaranteed prevention.')
else:
    st.warning('Do not start, stop, or change medicines based on this page. Symptoms, treatment choices and urgency depend on clinical evaluation.')
st.divider()
st.caption('Source: MedlinePlus.gov (U.S. National Library of Medicine). Results are updated by the source and cached by this app for up to 24 hours. MedPredict is not endorsed by NLM.')
