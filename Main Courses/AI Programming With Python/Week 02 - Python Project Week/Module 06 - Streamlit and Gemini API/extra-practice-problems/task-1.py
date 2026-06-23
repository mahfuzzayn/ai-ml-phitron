import streamlit as st

st.title("Personal Info Card App", anchor=False)

name = st.text_input("Your name: ")
age = st.number_input("Your age: ", min_value=1, max_value=100)
occupation = st.selectbox("Your occupation", ("Engineer", "Doctor"), accept_new_options=True)

button = st.button("Show details")

if button:
    if name and age and occupation:
        st.success("Successfully entered details")
        st.write("Name: ", name)    
        st.write("Age: ", age)    
        st.write("Occupation: ", occupation)    
    else:
        st.warning("Fields are missing fill them first")
        
        
    