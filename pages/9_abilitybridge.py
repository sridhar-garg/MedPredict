"""AbilityBridge: ready-to-use pretrained landmark ASL/ISL + Braille."""
from __future__ import annotations
import threading
import time
import streamlit as st
from braille_tools import braille_dots, text_to_braille, braille_to_text
from hand_tracking import LiveLandmarkState, create_detector, extract_landmarks
from sign_recognition import load_pretrained, classify, WEIGHTS

st.set_page_config(page_title="AbilityBridge | MedPredict X",page_icon="🤟",layout="wide")


from sidebar_compat import show_sidebar
show_sidebar()
try:
    from utils import apply_custom_css
    apply_custom_css()
except (ImportError, AttributeError):
    pass
if not st.session_state.get("is_logged_in", False):
    st.warning("Sign in to use AbilityBridge.")
    st.page_link("app.py", label="Back to sign in", icon="🏠")
    st.stop()
st.title("🤟 AbilityBridge")
st.caption("Pretrained ASL & ISL fingerspelling · Braille learning and conversion")
mode=st.radio("Choose a tool",["ASL fingerspelling", "ISL fingerspelling", "Braille"],horizontal=True)

if mode=="Braille":
    st.subheader("⠃ Braille Studio")
    st.write("Learn and convert **uncontracted English Grade 1 Braille**. This outputs Unicode symbols, not raised tactile dots or Grade 2 contractions.")
    text=st.text_area("Text to Braille",value="Hello MedPredict",height=100,max_chars=2000)
    converted=text_to_braille(text)
    st.text_area("Unicode Braille — copy or download",value=converted,height=120)
    st.download_button("Download Braille text",converted.encode('utf-8'),file_name="medpredict_braille.txt",mime="text/plain")
    sample=st.text_input("Braille to text",value="⠓⠑⠇⠇⠕",max_chars=500)
    st.code(braille_to_text(sample))
    st.divider()
    st.subheader("Learn the six-dot cell")
    selected=st.selectbox("Explore a letter",list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),index=0)
    char=text_to_braille(selected.lower()); active=set(braille_dots(char))
    left,right=st.columns([2,3])
    with left:
        for a,b in ((1,4),(2,5),(3,6)):
            a1,a2=st.columns(2)
            with a1:st.markdown(f"### {'🔵' if a in active else '⚪'}")
            with a2:st.markdown(f"### {'🔵' if b in active else '⚪'}")
    with right:
        st.metric(f"Letter {selected}",char)
        st.write("Raised dots:",", ".join(map(str,sorted(active))))
        st.caption("For real Braille access, use an embossed printout or a refreshable Braille display. A screen symbol alone is not tactile.")
    st.stop()



language = "ASL" if mode.startswith("ASL") else "ISL"
st.subheader("📷 " + ("American Sign Language" if language == "ASL" else "Indian Sign Language"))
st.write("Show a letter to the camera. The **already-trained landmark AI** recognises it, "
         "then types it after **0.4 seconds of stable detection**. No training or sample recording required.")
st.caption("The live camera is clean: no bounding boxes or landmark drawings. "
           "These models recognise individual static alphabet poses, not full signed conversation. "
           "Movement-based letters such as ASL J and Z may be unreliable.")

key=f"mp_pretrained_sign_state_{language}"
if key not in st.session_state:
    st.session_state[key]=LiveLandmarkState(language=language)
state=st.session_state[key]


if state.model is None:
    try:
        with st.spinner(f"Loading already-trained {language} landmark recognition model..."):
            ready_model=load_pretrained(language)
        with state.lock:
            state.model=ready_model
            state.reset_stability()
    except Exception as exc:
        st.error(f"Unable to load {language} pretrained model: {type(exc).__name__}: {str(exc)[:230]}")
        st.info("This model is downloaded automatically from its original public repository. "
                "Check your internet connection, then click Rerun. You do not need to train it.")
        if st.button("Retry loading the model",key=f"ability_retry_{language}"):
            st.rerun()
        st.stop()

st.success(f"{language} pretrained A–Z classifier is ready. Press START on the camera player.")
st.caption("Source: " + WEIGHTS[language]['credit'] + ". These are third-party model weights, "
           "not trained by the MedPredict developers. Model scores are not calibrated accuracy estimates.")
st.caption("Allow browser webcam access. Camera frames are processed on the Streamlit server and "
           "are not saved by AbilityBridge.")
try:
    import cv2
    import av
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
except ImportError as exc:
    st.error(f"Missing camera dependency: {exc}. Install requirements.txt and restart Streamlit.")
    st.stop()


def video_callback(frame):
    image = frame.to_ndarray(format="bgr24")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    now = time.monotonic()
    try:
        with state.lock:
            if state.detector is None:
                state.detector = create_detector()
            hands = extract_landmarks(state.detector, rgb)
            state.hand_count = len(hands)
            state.frame_count += 1
            if hands:

                label, score = classify(state.model, hands[0])
                state.observe(label, score, now, hand_present=True)
            else:
                state.observe(None, 0., now, hand_present=False)
            state.error = ""
    except Exception as exc:
        with state.lock:
            state.error = f"{type(exc).__name__}: {str(exc)[:190]}"
            state.observe(None, 0., now, hand_present=False)

    return av.VideoFrame.from_ndarray(image, format="bgr24")

ctx = webrtc_streamer(
    key=f"mp_pretrained_camera_{language}",
    mode=WebRtcMode.SENDRECV,
    video_frame_callback=video_callback,
    media_stream_constraints={"video":{"width":{"ideal":640},"height":{"ideal":480}},"audio":False},
    rtc_configuration={"iceServers":[{"urls":["stun:stun.l.google.com:19302"]}]},
    async_processing=False,
)
if not ctx.state.playing:
    st.caption("Click START. Some restricted networks require a TURN server for WebRTC on Streamlit Cloud.")

@st.fragment(run_every=0.4)
def live_typing():
    with state.lock:
        snap=state.get_status()
    st.subheader("Live sign typing")
    st.code(snap['typed'] if snap['typed'] else '(Hold a sign for 0.4 seconds)',language='text')
    st.caption(f"Detected: {snap['label'] or 'uncertain / no hand'} · "
               f"model score: {snap['score']:.0%} · "
               f"hands: {snap['hand_count']} · frames: {snap['frames']}")
    if snap['error']:
        st.warning("Camera or inference issue: " + snap['error'])
live_typing()

cols = st.columns(4)
for col,label,action in zip(cols,["Space","Backspace","New line","Clear"],
                            ["space","backspace","newline","clear"]):
    with col:
        if st.button(label,key=f"mp_pretrained_{language}_{action}",use_container_width=True):
            with state.lock:
                state.action(action)
            st.rerun()
with st.expander("Model details and limitations"):
    st.write("Uses Google MediaPipe hand landmarks and a separately trained letter-classification model. "
             "ASL and ISL use DIFFERENT feature normalization matching their source training code. "
             "This recognises static alphabet poses, not complete ASL/ISL sentences or dynamic signing. "
             "Recognition can be wrong for different signers, lighting, orientations and similar letters. "
             "To repeat the same letter, remove your hand briefly before making the gesture again.")
