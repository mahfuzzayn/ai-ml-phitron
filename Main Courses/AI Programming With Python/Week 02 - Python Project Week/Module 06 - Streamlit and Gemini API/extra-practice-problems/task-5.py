import streamlit as st
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

api_secret = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_secret)

st.title("Gemini Chatbot App")

question = st.text_area("Type your question: ")

button = st.button("Ask Gemini")

if button:
    if question:
        response = client.models.generate_content(model="gemini-3-flash-preview", contents=f"""
                                                  Always answer simply.
                                                  
                                                  Questions is:
                                                  {question}
                                                  
                                                  Roles:
                                                  You must answer this question within 100 words.
                                                  Answer professionally.
                                                  """)
        st.write(response.text)