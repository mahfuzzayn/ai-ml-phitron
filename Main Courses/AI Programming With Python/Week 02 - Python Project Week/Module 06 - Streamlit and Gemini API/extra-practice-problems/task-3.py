import streamlit as st

st.title("Audio & Video Player App", anchor=False)

file = st.file_uploader("Upload video or audio file", ["mp3", "wav", "mp4", "mkv"])

button = st.button("Click to play the media")

if button:
    if file:
        if (file.type.split("/")[0] == "video"):
            st.video(file)
        elif (file.type.split("/")[0] == "audio"):
            st.audio(file)
    else:
        st.error("No file were uploaded")