from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os
from datetime import datetime, timedelta

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças (Juros Diário em R$)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join("data", "clientes.json")
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# ---------- util ----------
def parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def dias_uteis_apos_vencimento(venc, hoje):
    """Conta dias úteis no intervalo (venc, hoje]."""
    if not venc or not hoje or hoje <= venc:
        return 0
    d = venc + timedelta(days=1)
    dias = 0
    while d <= hoje:
        if d.weekday() < 5:  # 0..4 = seg..sex
            dias += 1
        d += timedelta(days=1)
    return dias

def validar_cliente(cli: dict):
    obrig = ["nome","valor_credito","data_credito","data_vencimento",
             "juros_mensal","telefone"]
    for c in obrig:
        if str(cli.get(c,"")).strip() == "":
            raise HTTPException(400, f"O campo '{c}' é obrigatório.")

    tel = cli.get("telefone","").replace("+","").replace(" ","").replace("-","")
    if not tel.isdigit() or len(tel) < 10:
        raise HTTPException(400, "Telefone inválido. Use 5561XXXXXXXX.")
    cli["telefone"] = tel

    try:
        cli["valor_credito"] = float(cli["valor_credito"])
        cli["juros_mensal"] = float(cli["juros_mensal"])
    except Exception:
        raise HTTPException(400, "valor_credito/juros_mensal inválidos.")

    jd_val = cli.get("juros_diario_valor", cli.get("juros_diario", 0))
    try:
        cli["juros_diario_valor"] = float(jd_val or 0.0)
    except Exception:
        raise HTTPException(400, "juros_diario_valor inválido (use valor em R$ por dia útil).")

    dc = parse_date(cli.get("data_credito"))
    dv = parse_date(cli.get("data_vencimento"))
    if not dc or not dv:
        raise HTTPException(400, "Datas inválidas. Use YYYY-MM-DD ou DD/MM/YYYY.")
    cli["data_credito"] = dc.strftime("%Y-%m-%d")
    cli["data_vencimento"] = dv.strftime("%Y-%m-%d")
    return cli

def calcular_valores(cli: dict):
    valor_credito = float(cli.get("valor_credito", 0) or 0)
    juros_mensal  = float(cli.get("juros_mensal", 0) or 0)
    jd_r = float(cli.get("juros_diario_valor", 0) or 0)  # valor fixo em R$/dia útil

    venc = parse_date(cli.get("data_vencimento"))
    hoje = datetime.now().date()

    juros_mensal_valor = valor_credito * (juros_mensal / 100.0)
    dias_atraso = dias_uteis_apos_vencimento(venc, hoje)
    juros_diario_total = jd_r * dias_atraso

    valor_total = round(valor_credito + juros_mensal_valor + juros_diario_total, 2)

    cli["juros_mensal_valor"] = round(juros_mensal_valor, 2)
    cli["juros_diario_valor_dia"] = round(jd_r, 2)
    cli["juros_diario_total"] = round(juros_diario_total, 2)
    cli["dias_uteis_atraso"] = dias_atraso
    cli["valor_total"] = valor_total
    return cli

# ---------- rotas ----------
@app.get("/")
def home():
    return {"msg": "API LW ativa (juros diário em R$ por dia útil, após vencimento)."}

@app.get("/clientes")
def clientes():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        arr = json.load(f)
    return [calcular_valores(dict(c)) for c in arr]

@app.post("/cadastrar")
def cadastrar(cli: dict):
    cli = validar_cliente(cli)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        arr = json.load(f)
    arr.append(cli)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)
    return {"mensagem": "Cliente cadastrado."}

@app.post("/editar/{i}")
def editar(i: int, cli: dict):
    cli = validar_cliente(cli)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        arr = json.load(f)
    if 0 <= i < len(arr):
        arr[i] = cli
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2)
        return {"mensagem": "Cliente atualizado."}
    raise HTTPException(404, "Cliente não encontrado.")

@app.delete("/cliente/{i}")
def excluir(i: int):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        arr = json.load(f)
    if 0 <= i < len(arr):
        rm = arr.pop(i)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2)
        return {"mensagem": f"Cliente '{rm.get('nome')}' removido."}
    raise HTTPException(404, "Cliente não encontrado.")
