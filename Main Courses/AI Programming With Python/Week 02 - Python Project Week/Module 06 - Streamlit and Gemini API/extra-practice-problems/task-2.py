import streamlit as st

st.title("Image Gallery App", anchor=False)

images = st.file_uploader("Upload Images (Max 3 file)", ["jpeg", "jpg", "png"], accept_multiple_files=True)

if images:
    if (len(images) > 3):
        st.error("You cannot upload more than 3 image")
    else:
        cols = st.columns(len(images))
        
        for i, image in enumerate(images):
            with cols[i]:
                st.image(image)
