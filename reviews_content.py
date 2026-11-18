"""Account-backed community feedback and review submission."""
import streamlit as st
from database import get_reviews, save_review, delete_review

def review_card(item):
    with st.container(border=True):
        left, right = st.columns([4,1])
        with left:
            # User content is plain text, never interpolated into HTML or translated.
            st.markdown(item['title'], _mp_raw=True)
            st.text(f"{item['name']} · {item['context']}")
        with right:
            st.text('★' * item['rating'] + '☆' * (5-item['rating']))
        st.markdown(item['comment'], _mp_raw=True)
        st.caption('Submitted by a signed-in user · ' + str(item['updated_at'])[:10])


def render_reviews():
    reviews = get_reviews()
    a,b,c = st.columns(3)
    a.metric('Community rating', f"{sum(x['rating'] for x in reviews)/len(reviews):.1f} / 5" if reviews else '—')
    b.metric('Submitted reviews', len(reviews))
    c.metric('Languages available', '15')
    community, write = st.tabs(['Community reviews','Write a review'])
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
