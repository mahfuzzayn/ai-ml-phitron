import streamlit as st
from google import genai
import os
from dotenv import load_dotenv

st.title("Gemini Chat Bot")

load_dotenv()

api_secret = os.environ.get("GEMINI_API_KEY")
client = genai.Client()

prompt = st.text_area("Write your prompt here")

button = st.button("Generate Response")

if button:
    if prompt:
        try:
            response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
            
            st.write(response.text)
        except Exception as e:
            st.warning("There was an error running the model")
    else:
        st.error("Enter the prompt please")
    