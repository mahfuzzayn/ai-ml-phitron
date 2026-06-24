import streamlit as st

st.title("Calculator", anchor=False)

cols = st.columns(4)

x = 0
y = 0
operator = "+"
result = 0

with cols[0]:
    x = st.number_input("Enter number X")
    
with cols[1]:
    operator = st.selectbox("Operator", ("+", "-", "/", "*"))

with cols[2]:
    y = st.number_input("Enter number Y")


button = st.button("Answer")

if button:
    if x and y:
        result = x + y
    
        with cols[3]:
            st.header(f"{result:.0f}")
    else:
        st.error("Fill the numbers please")