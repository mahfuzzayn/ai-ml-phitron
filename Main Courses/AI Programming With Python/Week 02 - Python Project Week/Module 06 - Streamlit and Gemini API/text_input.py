import streamlit as st

st.write("Hello world")

st.title("My first Streamlit Web Apps", anchor=False)

st.header("Content 1", divider=True)

st.subheader("Content 1 Subheader")

st.markdown(":red[**Hello**] *World*")

st.markdown(":red-background[:orange[**Hello**] *World*] :world_map:")

a = 10

b = 20

st.write(a, b)