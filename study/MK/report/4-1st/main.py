import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document


st.title("4-1st Report")
st.write("Hello World")

file_path = 

with st.container():
    st.file_uploader("Upload a file", type=["txt", "pdf", "json", "csv"], accept_multiple_files=True)
    