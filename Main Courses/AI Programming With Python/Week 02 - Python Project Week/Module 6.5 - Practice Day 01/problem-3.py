import streamlit as st
from google import genai
import os
from dotenv import load_dotenv

st.title("Prompt Engineering by Gemini")
st.text("Model: Gemini 3 Flash Preview")

load_dotenv()

api_secret = os.environ.get("GEMINI_API_KEY")
client = genai.Client()

prompt = st.text_area("Write your prompt here")

button = st.button("Enhance prompt")

if button:
    if prompt:
        try:
            response = client.models.generate_content(model="gemini-3-flash-preview", contents=f"""Your job is to improve this given sentence professionally. Make sure the output only about the topic nothing else like to improve the sentence etc. Always output according to the input content size.
                                                      
                                                      Input:
                                                      {prompt}
                                                      """)
            
            st.write(response.text)
        except Exception as e:
            st.warning("There was an error running the model")
    else:
        st.error("Enter the prompt please")
    