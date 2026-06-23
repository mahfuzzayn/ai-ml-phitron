import streamlit as st

selected = st.selectbox("Choose your profession", ("Student", "Employee", "Businessman"), index=None, accept_new_options=True)

selected_numbers = st.selectbox("Choose your profession", (1, 2, 3), index=None, accept_new_options=True)

# print(type(selected))
print(type(selected_numbers))

# st.write("You selected", selected)
st.write("You selected", selected_numbers)