import streamlit as st
from api_calling import note_generator, audio_transcription, quiz_generator
from PIL import Image

# Title
st.title("Note Summary and Quiz Generator", anchor=False)
st.markdown("Upload upto 3 images to generate Note summary and Quizzes")
st.divider()

with st.sidebar:
    st.header("Controls")
    
    # Image
    images = st.file_uploader(
        "Upload the photos of your note",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )
    
    pil_images = []
    
    for img in images:
        pil_img = Image.open(img)
        pil_images.append(pil_img)
    
    if (images):
        if (len(images) > 3):
            st.error("Upload at max 3 images")
        else:
            st.subheader("Uploaded images")
            
            cols = st.columns(len(images))
            
            for i, image in enumerate(images):
                with cols[i]:
                    st.image(image)
                    
                    
    # Difficulty - Category
    
    selected_option = st.selectbox(
        "Enter the difficulty of your quiz", 
        ("Easy", "Medium", "Hard"),
        index = None
    )
    
    if selected_option:
        st.markdown(f"You selected **{selected_option}** as difficulty of your quiz")
    
    pressed = st.button("Click the button to initiate AI", type="primary")
    

if pressed:
    if not images:
        st.error("You must upload 1 image")
    if not selected_option:
        st.error("You must select a difficulty")
    
    if images and selected_option:
        # Note
        with st.container(border=True):
            st.subheader("Your Note")
            
            # The portion will be replaced by API Call
            
            with st.spinner("AI is writing notes for you"):
                generated_notes = note_generator(pil_images)
                st.markdown(generated_notes)
        
        # Audio Transcript
        with st.container(border=True):
            st.subheader("Your Audio")
            
            # The portion will be replaced by API Call
            with st.spinner("AI is preparing the audio"):
                
                # Filtering Output
                generated_notes = note_generator(pil_images).replace("#", "")
                generated_notes = note_generator(pil_images).replace("*", "")
                generated_notes = note_generator(pil_images).replace("-", "")
                generated_notes = note_generator(pil_images).replace("`", "")
                
                audio_transcription = audio_transcription(generated_notes)
                st.audio(audio_transcription)
        
        # Quiz
        with st.container(border=True):
            st.subheader(f"Quiz ({selected_option} Level) Difficulty")
            
            # The portion will be replaced by API Call
            
            with st.spinner("AI is generating the quizzes"):
                quizzes = quiz_generator(pil_images, selected_option)
                st.markdown(quizzes)
        