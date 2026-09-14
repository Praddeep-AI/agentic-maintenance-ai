# Agentic Maintenance AI — Deployable Repository

This folder is a **self-contained deployable app** for Streamlit Community Cloud, Docker, or IBM Cloud.

## Quick start (local)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy → Streamlit Community Cloud (free, 5 min)
1. Push this folder to a GitHub repo
2. Go to **https://share.streamlit.io** → New app
3. Set **Main file path** = `streamlit_app.py`
4. Click Deploy ✅

## Deploy → Docker
```bash
docker build -t agentic-maintenance .
docker run -p 8501:8501 agentic-maintenance
```

## Run tests
```bash
python -m pytest tests/ -v
```
