from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, json
from modules.clients.routes import router as clients_router
from modules.whatsapp.send_message import send_whatsapp_message, can_send_whatsapp

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients_router, prefix="")

@app.get("/")
def home():
    return {"mensagem": "API LW Mútuo Mercantil rodando"}

@app.post("/enviar_whatsapp/{index}")
async def enviar_whatsapp(index: int, request: Request):
    DATA_FILE = os.path.join("data", "clientes.json")
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="Sem dados")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        clientes = json.load(f)
    if index < 0 or index >= len(clientes):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cliente = clientes[index]
    phone = cliente.get("telefone")
    if not phone:
        raise HTTPException(status_code=400, detail="Telefone não cadastrado")
    message = f"Olá {cliente.get('nome')}!\nSua cobrança atualizada: R$ {cliente.get('valor_total')}\nDias: {cliente.get('dias_corridos')}\nPagamento via PIX: {os.getenv('PIX_INFO','(PIX não configurado)')}")
    if can_send_whatsapp():
        result = send_whatsapp_message(phone, message)
        return {"ok": True, "result": result}
    else:
        wa = f"https://wa.me/55{phone}?text={message}"
        return {"ok": False, "wa_link": wa, "note": "Envio via API não configurado, abra o link manualmente."}
