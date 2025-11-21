
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
import json
import os

DATA_FILE = "data/clientes.json"
FERIADOS_FIXOS = {(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(12,25)}
FERIADOS_DF_FIXOS = {(4,21),(11,30)}

PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a"
CNPJ_PIX = "59014280000130"

app = FastAPI(title="LW Mútuo Mercantil - Autocobranças")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_date_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")

def format_money_br(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def load_clientes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_clientes(lst):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)

def is_feriado(d: date) -> bool:
    if (d.month, d.day) in FERIADOS_FIXOS:
        return True
    if (d.month, d.day) in FERIADOS_DF_FIXOS:
        return True
    return False

def proximo_dia_util(d: date) -> date:
    while d.weekday() >= 5 or is_feriado(d):
        d += timedelta(days=1)
    return d

def contar_dias_uteis(inicio: date, fim: date) -> int:
    dias = 0
    d = inicio
    while d <= fim:
        if d.weekday() < 5 and not is_feriado(d):
            dias += 1
        d += timedelta(days=1)
    return dias

def aplicar_calculo(cli: dict):
    # Gera até 3 ciclos de vencimento (exemplo)
    ciclos = []
    valor_base = float(cli.get("valor_credito", 0) or 0)
    juros_mensal = float(cli.get("juros_mensal", 0) or 0)
    juros_diario_valor = float(cli.get("juros_diario_valor", 0) or 0)

    data_cred_str = cli.get("data_credito") or cli.get("data_vencimento")
    if not data_cred_str:
        cli["ciclos"] = []
        return

    d0 = datetime.strptime(data_cred_str, "%Y-%m-%d").date()
    venc_atual = cli.get("vencimento_atual")
    if venc_atual:
        d0 = datetime.strptime(venc_atual, "%Y-%m-%d").date()

    for i in range(3):
        venc = proximo_dia_util(d0 + timedelta(days=30*i))
        dias_uteis = contar_dias_uteis(d0, venc)
        juros_mensal_valor = valor_base * (juros_mensal/100.0)
        juros_diario_total = dias_uteis * juros_diario_valor
        valor_atualizado = valor_base + juros_mensal_valor + juros_diario_total

        ciclos.append({
            "indice": i+1,
            "vencimento": venc.strftime("%Y-%m-%d"),
            "dias_uteis": dias_uteis,
            "juros_mensal_valor": round(juros_mensal_valor, 2),
            "juros_diario_total": round(juros_diario_total, 2),
            "valor_atualizado": round(valor_atualizado, 2),
        })

    cli["ciclos"] = ciclos
    if not cli.get("vencimento_atual"):
        cli["vencimento_atual"] = ciclos[0]["vencimento"]

class ClienteIn(BaseModel):
    nome: str
    telefone: str
    valor_credito: float
    data_credito: Optional[str] = None
    data_vencimento: Optional[str] = None
    juros_mensal: float
    juros_diario_valor: float
    objeto: Optional[str] = None
    associados: Optional[List[str]] = []

@app.get("/clientes")
def listar_clientes():
    lst = load_clientes()
    for c in lst:
        aplicar_calculo(c)
    save_clientes(lst)
    return lst

@app.post("/cadastrar")
def cadastrar(cli: ClienteIn):
    lst = load_clientes()
    d = cli.dict()
    if not d.get("data_credito"):
        d["data_credito"] = datetime.now().strftime("%Y-%m-%d")
    if not d.get("data_vencimento"):
        d["data_vencimento"] = d["data_credito"]
    d["status"] = "ativo"
    d["vencimento_atual"] = d["data_vencimento"]
    lst.append(d)
    save_clientes(lst)
    return {"ok": True, "index": len(lst)-1}

@app.post("/editar/{idx}")
def editar(idx: int, cli: ClienteIn):
    lst = load_clientes()
    if idx < 0 or idx >= len(lst):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    d = cli.dict()
    antigo = lst[idx]
    d.setdefault("status", antigo.get("status", "ativo"))
    d.setdefault("vencimento_atual", antigo.get("vencimento_atual", d.get("data_vencimento")))
    lst[idx] = d
    save_clientes(lst)
    return {"ok": True}

@app.get("/cobrancas/hoje")
def cobrancas_hoje():
    lst = load_clientes()
    for c in lst:
        aplicar_calculo(c)
    save_clientes(lst)

    hoje_iso = datetime.now().date().strftime("%Y-%m-%d")
    cobrancas = []

    for i, cli in enumerate(lst):
        if cli.get("vencimento_atual") != hoje_iso:
            continue

        status = (cli.get("status") or "ativo").lower()
        if status == "quitado":
            continue

        ciclos = cli.get("ciclos") or []
        ciclo_atual = next(
            (ci for ci in ciclos if ci.get("vencimento") == cli.get("vencimento_atual")),
            None
        )
        if not ciclo_atual and ciclos:
            ciclo_atual = ciclos[-1]

        valor = float(
            ciclo_atual.get("valor_atualizado")
            if ciclo_atual else cli.get("valor_credito", 0.0)
        )

        dt_venc = datetime.strptime(cli["vencimento_atual"], "%Y-%m-%d").date()
        data_venc_br = format_date_br(dt_venc)
        objeto = cli.get("objeto") or ""

        msg_partes = []
        msg_partes.append(f"Olá {cli.get('nome','')}, tudo bem?\n\n")
        msg_partes.append("Aqui é da LW Mútuo Mercantil.\n\n")
        texto_contrato = f"Estamos lembrando que hoje, dia {data_venc_br}, vence o pagamento referente ao seu contrato."
        if objeto:
            texto_contrato += f" Objeto em garantia: {objeto}."
        msg_partes.append(texto_contrato + "\n\n")
        msg_partes.append(
            f"Valor para pagamento hoje (com juros do mês e juros diário conforme combinado): {format_money_br(valor)}.\n\n"
        )
        msg_partes.append("Chaves PIX para pagamento:\n")
        msg_partes.append(f"• Chave padrão: {PIX_KEY}\n")
        msg_partes.append(f"• CNPJ: {CNPJ_PIX}\n\n")
        msg_partes.append(
            "Após o pagamento, por favor envie o comprovante neste número para atualização do sistema.\n\n"
        )
        msg_partes.append("Qualquer dúvida, estamos à disposição.")
        mensagem = "".join(msg_partes)

        cobrancas.append({
            "indice": i,
            "nome": cli.get("nome"),
            "telefone": cli.get("telefone"),
            "data_vencimento": data_venc_br,
            "valor_com_juros": valor,
            "mensagem_whatsapp": mensagem,
            "status": status,
        })

    return cobrancas

@app.get("/")
def root():
    return {"status": "ok"}
