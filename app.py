import streamlit as st
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template


import cv2
import pytesseract

import tempfile

def image_to_text(image_file):
    # Create a temporary file
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(image_file.read())

    # Read the image file
    img = cv2.imread(tfile.name)

    # Convert the image to gray scale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Use Tesseract to extract text
    text = pytesseract.image_to_string(gray)

    return text

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(raw_text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(raw_text)
    return chunks

def get_vectorstore(chunks):
    embeddings = OpenAIEmbeddings()
    vectorStore = None  # default value
    
    if not chunks or all(not chunk for chunk in chunks):
        st.error("No valid text chunks found in the audio file.")
    else:
        vectorStore = FAISS.from_texts(chunks, embedding=embeddings)
    
    return vectorStore

def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            


def audio_to_text(audio_file):
    audio = AudioSegment.from_wav(audio_file, parameters=["-analyzeduration", "2147480000", "-probesize", "2147480000"])
    # rest of your code
    audio.export("temp.wav", format="wav")
    

    # transcribe audio file
    recognizer = sr.Recognizer()
    with sr.AudioFile('temp.wav') as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language='no-NO')
    
    return text

def main():
    load_dotenv()
    st.set_page_config(page_title='Chat with PDF', page_icon=':books:')
    st.write(css, unsafe_allow_html=True)

    st.session_state.conversation = st.session_state.get('conversation', None)
    st.session_state.chat_history = st.session_state.get('chat_history', None)

    st.header('Chat with PDF :books:')
    user_question = st.text_input('Ask a Question about your documents')
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader('Your Documents')
        pdf_docs = st.file_uploader('Upload PDFs', accept_multiple_files=True)
        audio_files = st.file_uploader("Upload audio files", type=['wav'], accept_multiple_files=True)
        image_files = st.file_uploader("Upload image files", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
        if st.button('Process'):
            with st.spinner('Processing'):
                text_chunks = []

                if pdf_docs:
                    # get the pdf text
                    raw_text = get_pdf_text(pdf_docs)
                    # get text chunks 
                    text_chunks.extend(get_text_chunks(raw_text))

                if audio_files is not None:
                    for audio_file in audio_files:
                        # convert audio to text
                        raw_text = audio_to_text(audio_file)
                        # get text chunks 
                        text_chunks.extend(get_text_chunks(raw_text))

                
                if image_files is not None:
                    for image_file in image_files:
                        # convert image to text
                        raw_text = image_to_text(image_file)
                        # get text chunks
                        text_chunks.extend(get_text_chunks(raw_text))

                # create vector store
                vectorstore = get_vectorstore(text_chunks)
                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)

if __name__ == '__main__':
    main()