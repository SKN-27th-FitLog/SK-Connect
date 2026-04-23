from glob import glob
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


##############################################################################################
# text data loader
##############################################################################################
def load_text_data(file_path):
    """ 지정한 경로의 파일을 로드한 뒤 해당 데이터를 document 객체로 반환한다. """

    ##############################################
    # 문서 파일 로드해서 document 로 변환 
    ##############################################

    # 폴더에 있는 파일 읽기 
    files = glob(file_path)

    # 파일 로더 
    loader = DirectoryLoader(
        path = file_path,
        glob = ".txt",
        show_progress=True,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    # 파일 로드 
    docs = loader.load()

    ##############################################
    # 문서 파일 스플릿 
    ##############################################

    # 스플리터 
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=30)

    # 문서 스플릿 
    docs = splitter.split_documents(docs)

    return docs