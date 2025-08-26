import os
import requests
import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import json
import pytesseract
from PIL import Image
import io
from gtts import gTTS


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



st.set_page_config(page_title="OCR + TTS", layout="wide")
st.title("EchoDocs")

# openai key 
openai_api_key = st.secrets["OPENAI_API_KEY"]
openai_client = OpenAI(api_key=openai_api_key)



# helper functions 
def save_file(data, filename, folder):
    # save into folder
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path,"wb") as f:
            f.write(data)
        return True, path
    except Exception as e:
        return False,str(e)



def run_ocr(file_bytes, filename="input.png"):
    # tesseract OCR (english only for now)
    try:
        img = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(img, lang="eng")   
        return text.strip()
    except Exception as e:
        st.error("OCR error: " + str(e))
        return None



def run_tts(text, slow_mode=False):
    # text to speech gTTS
    try:
        tts = gTTS(text=text, lang="en", slow=slow_mode)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        st.error("TTS failed: " + str(e))
        return None



def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        txt = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                txt.append(t)
        return "\n".join(txt).strip()
    except Exception as e:
        st.error("PDF error: "+str(e))
        return ""



def reading_stats(text):
    words = text.split()
    wc = len(words)
    mins = round(wc/150,2)  
    return wc, mins




if "results" not in st.session_state:
    st.session_state["results"] = []
if "last_text" not in st.session_state:
    st.session_state["last_text"] = ""




# Tabs 
tab1, tab2, tab3 = st.tabs(["📷 Image Upload", "📄 PDF Upload", "🌐 URL Input"])



# ---- Tab 1: Image ----
with tab1:
    up_img = st.file_uploader("Upload an image", type=["png","jpg","jpeg"])

    if up_img:
        st.image(up_img, caption="Uploaded", use_container_width=True)

        if st.button("Run OCR on Image"):
            with st.spinner("Extracting text..."):
                text = run_ocr(up_img.read(), up_img.name)

            if text:
                st.session_state["last_text"] = text
                st.success("done")
                st.write(text)

                wc, mins = reading_stats(text)
                st.info("Word Count: "+str(wc)+" | Reading Time: "+str(mins)+" mins")

                st.download_button("📥 TXT", text, file_name="ocr_result.txt")
                st.download_button("📥 JSON", json.dumps({"text": text}, indent=2), file_name="ocr_result.json")

        if st.session_state["last_text"]:
            slow = st.checkbox("Slow voice (tts)", value=False)
            if st.button("Generate Audio from Image"):
                with st.spinner("making audio..."):
                    audio = run_tts(st.session_state["last_text"], slow_mode=slow)
                if audio:
                    st.session_state["results"].append({
                        "text": st.session_state["last_text"],
                        "voice": "gTTS",
                        "content": audio
                    })
                    st.success("audio generated!")



# ---- Tab 2: PDF ----
with tab2:
    up_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
    if up_pdf:
        if st.button("Extract & OCR PDF"):
            with st.spinner("reading PDF..."):
                text = extract_text_from_pdf(up_pdf)

                if not text:   # fallback to OCR
                    up_pdf.seek(0)
                    text = run_ocr(up_pdf.read(), up_pdf.name)

            if text:
                st.session_state["last_text"] = text
                st.success("pdf extracted")
                st.write(text[:800] + ("..." if len(text) > 800 else ""))

                wc, mins = reading_stats(text)
                st.info(f"Words: {wc} | Time: {mins} mins")

                st.download_button("📥 TXT", text, file_name="pdf_result.txt")
                st.download_button("📥 JSON", json.dumps({"text": text}, indent=2), file_name="pdf_result.json")

        if st.session_state["last_text"]:
            slow = st.checkbox("Slow voice (pdf)", value=False)
            if st.button("Generate Audio from PDF"):
                with st.spinner("tts generating..."):
                    audio = run_tts(st.session_state["last_text"], slow_mode=slow)
                if audio:
                    st.session_state["results"].append({
                        "text": st.session_state["last_text"],
                        "voice": "gTTS",
                        "content": audio
                    })
                    st.success("pdf audio ready!")



# ---- Tab 3: URL ----
with tab3:
    url = st.text_input("Enter Image/PDF URL")
    if st.button("Run OCR on URL") and url:
        with st.spinner("fetching..."):
            try:
                resp = requests.get(url, stream=True, timeout=60)
                resp.raise_for_status()
                fbytes = resp.content
                text = run_ocr(fbytes, os.path.basename(url))

                if text:
                    st.session_state["last_text"] = text
                    st.success("URL OCR success")
                    st.write(text[:700] + ("..." if len(text) > 700 else ""))

                    wc, mins = reading_stats(text)
                    st.info("Words: "+str(wc)+" | Time: "+str(mins)+" mins")

                    st.download_button("📥 TXT", text, file_name="url_result.txt")
                    st.download_button("📥 JSON", json.dumps({"text": text}, indent=2), file_name="url_result.json")

            except Exception as e:
                st.error("URL error: "+str(e))

    if st.session_state["last_text"]:
        slow = st.checkbox("Slow voice (url)", value=False)
        if st.button("Generate Audio from URL OCR"):
            with st.spinner("generating audio..."):
                audio = run_tts(st.session_state["last_text"], slow_mode=slow)
            if audio:
                st.session_state["results"].append({
                    "text": st.session_state["last_text"],
                    "voice": "gTTS",
                    "content": audio
                })
                st.success("audio from url created!")



# ---- results ----
if st.session_state["results"]:
    st.subheader("Generated Audio Files")
    for idx, item in enumerate(st.session_state["results"]):
        with st.expander(f"Audio {idx+1} ({item['voice']})", expanded=(idx == len(st.session_state["results"]) - 1)):
            st.markdown("**Extracted Text Preview:** " + item['text'][:300] + ("..." if len(item['text'])>300 else ""))
            st.audio(item["content"], format="audio/mp3")

            if st.button("Save Audio "+str(idx+1), key=f"save_{idx}"):
                fname = f"Audio_{idx+1}.mp3"
                ok, path = save_file(item["content"], fname, "audio_output")
                if ok:
                    st.success("saved at "+path)
                else:
                    st.error("could not save audio")



# footer 
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #999;">
        <p>Mini Project - OCR & TTS (english only)</p>
    </div>
    """,
    unsafe_allow_html=True
)
