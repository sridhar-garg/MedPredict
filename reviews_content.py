"""Account-backed visitor feedback, kept separate from illustrative examples."""
import streamlit as st
from database import get_reviews, save_review, delete_review
from ui import html, icon

DEMO_REVIEWS = [
    dict(name='Demo reviewer 01', context='Sample interface walkthrough', rating=5,
         title='A clear place to start', comment='The assessment choices are easy to find, and the next step is clear.'),
    dict(name='Demo reviewer 02', context='Sample readability check', rating=4,
         title='Explanations in plain language', comment='The explanations make the model output easier to follow. A glossary would make unfamiliar terms even clearer.'),
    dict(name='Demo reviewer 03', context='Sample navigation check', rating=5,
         title='Everything feels connected', comment='Moving between assessments, reports and the help tools feels straightforward.'),
]


def review_card(item, sample=False):
    with st.container(border=True):
        left, right = st.columns([4,1])
        with left:
            # User content is plain text, never interpolated into HTML or translated.
            st.markdown(item['title'], _mp_raw=True)
            st.text(f"{item['name']} · {item['context']}")
        with right:
            st.text('★' * item['rating'] + '☆' * (5-item['rating']))
        st.markdown(item['comment'], _mp_raw=True)
        st.caption('Fictional example' if sample else 'Submitted by a signed-in user · ' + str(item['updated_at'])[:10])


def render_reviews():
    html(f'<div class="mp-page-intro"><span class="mp-eyebrow">COMMUNITY / YOUR VOICE</span>'
         f'<h1>Made better, together.</h1><p>Share what worked, what helped, and what could be clearer.</p></div>')
    reviews = get_reviews()
    a,b,c = st.columns(3)
    a.metric('Community rating', f"{sum(x['rating'] for x in reviews)/len(reviews):.1f} / 5" if reviews else '—')
    b.metric('Submitted reviews', len(reviews))
    c.metric('Languages available', '15')
    community, write, samples, usage = st.tabs(['Community reviews','Write a review','Sample reviews','Real-life usage'])
    with community:
        st.caption('Ratings reflect interface experience, not medical accuracy. One review per account; reviewers may update or delete their review.')
        if not reviews:
            st.info('Be the first to share your experience.')
        for item in reviews:
            review_card(item)
    with write:
        if not st.session_state.get('is_logged_in'):
            st.info('Sign in to submit a review.')
            st.page_link('app.py',label='Login')
        else:
            user_id=st.session_state.user_id
            own=get_reviews(user_id)
            current=own[0] if own else {}
            with st.form('community_review'):
                name=st.text_input('Display name',value=current.get('name',''),max_chars=60)
                rating=st.select_slider('Rating',options=[1,2,3,4,5],value=current.get('rating',5),format_func=lambda x:f'{x} / 5')
                context=st.selectbox('What did you try?', ['Assessments','Reports','AI assistant','Accessibility tools','Family health','Dashboard'],
                                     index=['Assessments','Reports','AI assistant','Accessibility tools','Family health','Dashboard'].index(current.get('context','Dashboard')))
                title=st.text_input('Review title',value=current.get('title',''),max_chars=100)
                comment=st.text_area('Your review',value=current.get('comment',''),max_chars=1500,height=160)
                st.caption('Use a public display name and keep personal health details out of your review.')
                consent=st.checkbox('I used MedPredict and agree to publish this review with my display name.')
                submit=st.form_submit_button('Update review' if own else 'Submit review',type='primary')
            if submit:
                if not consent:
                    st.warning('Please confirm that you used MedPredict and want to publish your review.')
                else:
                    try:
                        save_review(user_id,name,rating,title,comment,context)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error('Your review could not be saved. Please try again.')
                    else:
                        st.success('Your review has been saved. It will be here when you sign in again.')
                        st.rerun()
            if own:
                with st.expander('Delete my review'):
                    if st.button('Delete',key='delete_my_review'):
                        delete_review(user_id)
                        st.rerun()
    with samples:
        st.info('These three reviews are fictional examples from the original design. They are excluded from community ratings.')
        for item in DEMO_REVIEWS:
            review_card(item,sample=True)
    with usage:
        st.subheader('Real-life usage')
        st.write('The community rating above is calculated from submitted reviews only. No clinical validation or patient outcomes are claimed.')
        for context in ['Assessments','Reports','AI assistant','Accessibility tools','Family health','Dashboard']:
            count=sum(x['context']==context for x in reviews)
            if count: st.metric(context,count)
        if not reviews: st.info('No visitor feedback has been submitted yet.')
