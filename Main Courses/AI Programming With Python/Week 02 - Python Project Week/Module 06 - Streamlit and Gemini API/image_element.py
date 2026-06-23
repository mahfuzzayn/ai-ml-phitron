import streamlit as st

st.title("Input your files", anchor=False)
st.divider()

st.image("images/image-1.jpg")
st.image("https://cdn.pixabay.com/photo/2024/05/26/10/15/bird-8788491_1280.jpg")

st.divider()

images = st.file_uploader("Enter your image (at max 2)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

print(type(images))

if images:
    if (len(images) > 2):
        st.error("You uploaded 3 photos")
    
    col = st.columns(len(images))
    
    for i, per_image in enumerate(images):
        with col[i]:
            st.image(per_image)
    