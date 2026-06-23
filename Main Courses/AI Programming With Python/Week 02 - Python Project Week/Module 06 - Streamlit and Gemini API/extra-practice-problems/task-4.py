import streamlit as st

st.title("Text Style Explorer", anchor=False)

text = st.text_input("Enter your input")

if text:
    st.title(text)
    st.header(text)
    st.subheader(text)
    st.text(text)