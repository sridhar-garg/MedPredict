"""Reusable save controls and private, account-scoped activity history."""
import streamlit as st
from database import save_workspace_item, get_workspace_items, delete_workspace_item


def save_work(kind, title, payload):
    try:
        save_workspace_item(st.session_state.get('user_id'),kind,title,payload)
    except Exception:
        st.error('Your result could not be saved. Please try again.')
        return False
    st.success('Saved to your workspace.')
    return True


def save_control(kind,title,payload,key):
    if st.button('Save to my workspace',key=key):
        save_work(kind,title,payload)


def render_saved_workspace():
    st.subheader('Saved workspace')
    st.caption('Your saved screenings, report summaries, research results, accessibility work and conversations are linked to your account.')
    user_id=st.session_state.get('user_id')
    items=get_workspace_items(user_id)
    options=['All tools']+sorted({x['kind'] for x in items})
    selected=st.selectbox('Filter saved work',options,key='saved_kind')
    if not items: st.info('Your saved work will appear here.')
    for item in items:
        if selected!='All tools' and item['kind']!=selected: continue
        with st.expander(f"{item['title']} · {item['created_at'][:16]}"):
            payload=item['payload']
            if item['kind']=='AI assistant':
                for message in payload.get('messages',[]):
                    st.text(message.get('role','').capitalize())
                    st.markdown(message.get('content',''), _mp_raw=True)
            else:
                st.json(payload)
            st.download_button('Download saved item',__import__('json').dumps(payload,ensure_ascii=False,indent=2),
                               file_name=f"medpredict-{item['id']}.json",mime='application/json',key=f"export_{item['id']}")
            if st.button('Delete',key=f"delete_item_{item['id']}"):
                delete_workspace_item(user_id,item['id'])
                st.rerun()
