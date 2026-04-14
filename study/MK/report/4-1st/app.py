import streamlit as st
import tempfile
import pathlib
import os

from langchain_community.document_loaders import TextLoader, CSVLoader, JSONLoader, PyPDFLoader

FILE_TYPE_LOADER = {
    "txt": TextLoader,
    "csv": CSVLoader,
    "json": JSONLoader,
    "pdf": PyPDFLoader,
}

valid_files = []
documents = []

def validation_files(uploaded_files):
    for file in uploaded_files:
        expr = pathlib.Path(file.name).suffix.lstrip(".").lower()
        if expr not in FILE_TYPE_LOADER.keys():
            st.error(f"{file.name}은 지원하지 않는 형식입니다")
            continue
        else:
            valid_files.append((file, expr))
    return valid_files

def get_loader(expr, path):
    loader_type = FILE_TYPE_LOADER.get(expr)
    if expr == 'json':
        return loader_type(file_path=path, jq_schema=".", text_content=False)
    else:
        return loader_type(file_path=path)

def process_documents(valid_files:tuple):
    for file, expr in valid_files:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.getvalue())
            path = tmp.name
        try:
            loader = get_loader(expr, path)
            documents = loader.load()
            yield documents
        except Exception as e:
            st.error(f"파일 로드 중 오류가 발생했습니다: {e}")
        finally:
            if os.path.exists(path):
                os.remove(path)

def display_documents(documents):
    for docs in documents:
        if not docs:
            continue

        combined_content = "\n".join([doc.page_content for doc in docs])
        st.write(f"{docs[0].metadata.get('source', '파일')} 로드 완료")
        st.success(combined_content[:100] + "...")

if __name__ == "__main__":
    st.title(" File Loader")
    uploaded_files = st.file_uploader(
        label="",
        type = list(FILE_TYPE_LOADER.keys()),
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("파일을 업로드하세요")
    else:
        valid_files = validation_files(uploaded_files)
        documents = process_documents(valid_files)
        display_documents(documents)