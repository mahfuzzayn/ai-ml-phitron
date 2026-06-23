import streamlit as st

st.title("Input your Information", anchor=False)
st.divider()

name = st.text_input("Enter your name")

st.write("Your name is: ", name)

st.divider()

age = st.number_input("Enter your age", value=None, placeholder="Type your age..")

st.write("Your age is: ", age)

password = st.text_input("Enter your password", type="password")

st.write(password)

pressed = st.button("Enter to confirm", type="primary")

if pressed:
    st.write(f"Your name is {name} and your age is {age}")