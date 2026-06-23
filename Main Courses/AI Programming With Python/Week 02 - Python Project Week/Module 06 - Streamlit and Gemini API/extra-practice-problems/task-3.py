import streamlit as st

st.title("Audio & Video Player App", anchor=False)

file_uploader = st.file_uploader("Upload video or audio file", ["mp3", "wav", "mp4", "mkv"])

button = st.button("Click to play the media")

if button:
    if file_uploader:
        print(file_uploader)
    else:
        st.error("No file were uploaded")