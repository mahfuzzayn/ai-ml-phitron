from google import genai
from dotenv import load_dotenv
from gtts import gTTS
import os
import io

# Loading the environment variable
load_dotenv() 

my_api_key = os.environ.get("GEMINI_API_KEY")

# Initializing a client
client = genai.Client(api_key=my_api_key)

# Note generator
def note_generator(images):
    prompt = """"Summarize the picture in note format at max 100 words, make sure to add necessary markdown to differentiate different section"""
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[images, prompt]
    )
    
    return response.text

# Audio Generator
def audio_transcription(text):
    speech = gTTS(text, lang="en", slow=False)
    audio_buffer = io.BytesIO()
    speech.write_to_fp(audio_buffer)
    return audio_buffer


# Quiz generator
def quiz_generator(images, difficulty):
    prompt = f""""Generate 3 quizzes based on the {difficulty}. Make sure to add markdown to differentiate the options. Add correct answer too, after the quiz"""
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[images, prompt]
    )
    
    return response.text