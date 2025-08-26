conda create -n ocrenv python=3.11 -y

conda activate ocrenv

pip install -r requirements.txt

streamlit run app.py
