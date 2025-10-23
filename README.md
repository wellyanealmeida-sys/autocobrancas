LW Mútuo Mercantil - AutoCobranças
Execução local:
1) python -m venv venv
2) source venv/bin/activate   (ou venv\Scripts\activate no Windows)
3) pip install -r requirements.txt
4) uvicorn app:app --reload --host 0.0.0.0 --port 8000
5) python -m http.server 8080 --directory docs
Ajuste API endpoint em docs/script.js (API_BASE) para produção.
Configure WHATSAPP_TOKEN and WHATSAPP_PHONE_ID como secrets no Render para envio via Cloud API.
