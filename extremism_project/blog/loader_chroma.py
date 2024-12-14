import os
import nltk
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma


nltk.download('punkt')
nltk.download('averaged_perceptron_tagger_eng')

os.environ['OPENAI_API_KEY'] = '???'
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '???'

def load_chroma(persist_folder):
    print("Loading existing Chroma database...")
    vectorstore = Chroma(persist_directory=persist_folder, embedding_function=OpenAIEmbeddings(), collection_name='rag-chroma')
    return vectorstore

def create_chroma(data_folder, persist_folder):
    # Set up environment variables

    # Use DirectoryLoader to load documents from the folder
    loader = DirectoryLoader(data_folder)

    # Load the contents of each file into a list of documents
    docs = loader.load()

    # Combine all documents into one list
    docs_list = [doc for doc in docs]

    # Semantic split
    # Split the text of documents into fragments
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=300, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)
    print(len(doc_splits))
    
    # Add fragments to the vector database
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OpenAIEmbeddings(),
        persist_directory=persist_folder
    )
    
    # Persist the vector store to disk
    print(vectorstore.get())
    return vectorstore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(BASE_DIR, 'blog/data/MD')
DATA_ROOT_EN = os.path.join(BASE_DIR, 'blog/data_en/MD')
DATA_ROOT_KZ = os.path.join(BASE_DIR, 'blog/data_kz/MD')
CHROMA_ROOT = os.path.join(DATA_ROOT, 'vectorstore')
CHROMA_ROOT_EN = os.path.join(DATA_ROOT_EN, 'vectorstore')
CHROMA_ROOT_KZ = os.path.join(DATA_ROOT_KZ, 'vectorstore')
print(BASE_DIR)
#create_chroma(DATA_ROOT, CHROMA_ROOT)
#create_chroma(DATA_ROOT_EN, CHROMA_ROOT_EN)
#create_chroma(DATA_ROOT_KZ, CHROMA_ROOT_KZ)
