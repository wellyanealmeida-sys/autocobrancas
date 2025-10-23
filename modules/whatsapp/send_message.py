import os, requests

WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID')
WHATSAPP_API_URL = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages" if WHATSAPP_PHONE_ID else None

def can_send_whatsapp():
    return bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)

def send_whatsapp_message(phone, text):
    if not can_send_whatsapp():
        return {"error":"WhatsApp não configurado"}
    headers = {'Authorization': f'Bearer {WHATSAPP_TOKEN}', 'Content-Type': 'application/json'}
    payload = {"messaging_product":"whatsapp","to":phone,"type":"text","text":{"body":text}}
    resp = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=15)
    try:
        return resp.json()
    except Exception:
        return {"status_code": resp.status_code, "text": resp.text}
