import streamlit as st


st.title("Input your audio files (wav)", anchor=False)
st.divider()

st.video("video/video-1.mp4", loop=True)

video_file = st.file_uploader("Enter your video", type=["mp4", "mkv", "mov"])

print(type(video_file))

button = st.button("Click to upload")

if button:
    if video_file:
         st.video(video_file)
         st.success("Your file is uploaded successfully")
    else:
        st.error("You must upload file")