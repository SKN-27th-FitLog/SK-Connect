import json
import os
import tempfile

import streamlit as st
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader, JSONLoader
from langchain_core.documents import Document

import enum

st.title("File Loader")

class FILE_TYPE(enum.Enum):
    TXT = "txt"
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"

FILE_TYPE_LOADER = {
    FILE_TYPE.TXT: TextLoader,
    FILE_TYPE.PDF: PyPDFLoader,
    FILE_TYPE.CSV: CSVLoader,
    FILE_TYPE.JSON: JSONLoader,
}

documents: list[Document] = []

def check_exception(uploaded_files):
    for files in uploaded_files:
        if files not in FILE_TYPE_LOADER.keys():
            print(f"{files}은 지원하지 않는 형식입니다")
            uploaded_files = uploaded_files.remove(files)

def upload_files(documents):
    uploaded_files = st.file_uploader(
        label="",
        type=[ft.value for ft in FILE_TYPE],
        accept_multiple_files=True,
    )
    check_exception(uploaded_files)

    loader = FILE_TYPE_LOADER[uploaded_files]
    loaded = loader.load()
    documents.extend(loaded)

def read_files(documents):
    for document in documents:
        st.write(document.page_content[:100])
        st.write(document.metadata)


st.button("Upload", on_click=upload_files(documents))

st.text_area("Documents", value=read_files(documents))