import requests
import json
import streamlit as st
import base64
from io import BytesIO
from PIL import Image

# Accept multiple images
images = st.file_uploader(
    "Upload your images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

button = st.button("Prepare Notes")

if button:
    if not images:
        st.error("Please upload at least one image")
    else:
        # Convert uploaded files to base64
        image_contents = []
        for img_file in images:
            img = Image.open(img_file)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            b64 = base64.b64encode(buffered.getvalue()).decode()
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })

        prompt = """Summarize the content from these images in structured note format.
Use markdown (headings, bullet points, bold text) to organize different sections.
Keep the total under 200 words. Focus on key concepts, definitions, and important points.
Also generate 3 quiz questions at the end based on the summarized content."""

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": "Bearer <>",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "google/nemotron-3.5-content-safety:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            *image_contents
                        ]
                    }
                ]
            })
        )

        result = response.json()

        if "error" in result:
            st.error(f"API Error: {result['error'].get('message', result['error'])}")
            st.json(result)
        else:
            content = result['choices'][0]['message']['content']
            st.markdown(content)
