import streamlit as st

st.set_page_config(
    page_title="{{ project_name }}",
    page_icon="🚀",
    layout="wide",
)

st.title("{{ project_name }}")
st.markdown("{{ description }}")

with st.sidebar:
    st.header("Settings")
    name = st.text_input("Your name", value="World")

st.write(f"Hello, **{name}**!")

col1, col2 = st.columns(2)
with col1:
    st.metric("Temperature", "22 °C", "1.2 °C")
    st.metric("Humidity", "65%", "-3%")
with col2:
    st.metric("Wind", "12 km/h", "2 km/h")
    st.metric("Pressure", "1013 hPa", "0 hPa")

st.subheader("Data Preview")
st.dataframe({
    "Column A": [1, 2, 3, 4],
    "Column B": [10, 20, 30, 40],
    "Column C": ["a", "b", "c", "d"],
})

if st.button("About"):
    st.info("Built with Streamlit")
