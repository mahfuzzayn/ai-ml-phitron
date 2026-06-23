import streamlit as st


st.title("Input your audio files (wav)", anchor=False)
st.divider()

st.audio("audio/RMouseClick.wav", loop=True)

audio = st.file_uploader("Enter your audio", type=["mp3", "ogg", "flac", "wav"])

print(type(audio))

if audio:
    st.audio(audio)