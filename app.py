from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os
from datetime import datetime, timedelta

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças (Modelo Oficial)")

# CORS para o frontend (GitHub Pages)
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


# ---------- Utilidades ----------

def parse_date(date_str: str):
    """Tenta YYYY-MM-DD e DD/MM/YYYY."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue
    return None

def contar_dias_uteis(inicio_exclusivo, fim_inclusivo):
    """
    Conta apenas dias úteis (seg–sex) no intervalo (inicio_exclusivo, fim_inclusivo].
    Se hoje <= vencimento: 0.
    """
    if fim_inclusivo is None or inicio_exclusivo is None:
        return 0
    if fim_inclusivo <= inicio_exclusivo:
        return 0
    d = inicio_exclusivo + timedelta(days=1)  # começa no dia seguinte ao início
    dias = 0
    while d <= fim_inclusivo:
        if d.weekday() < 5:  # 0=segunda ... 4=sexta
            dias += 1
        d += timedelta(days=1)
    return dias

def validar_cliente(cliente: dict):
    obrig = ["nome", "valor_credito", "data_credito", "data_vencimento", "juros_mensal", "juros_diario", "telefone"]
    for campo in obrig:
        if str(cliente.get(campo, "")).strip() == "":
            raise HTTPException(status_code=400, detail=f"O campo '{campo}' é obrigatório.")

    # normaliza telefone
    tel = cliente["telefone"].replace("+", "").replace(" ", "").replace("-", "")
    if not tel.isdigit() or len(tel) < 10:
        raise HTTPException(status_code=400, detail="Telefone inválido. Use o formato 5561XXXXXXXX.")
    cliente["telefone"] = tel

    # numéricos
    try:
        cliente["valor_credito"] = float(cliente["valor_credito"])
        cliente["juros_mensal"] = float(cliente["juros_mensal"])
        cliente["juros_diario"] = float(cliente["juros_diario"])
    except Exception:
        raise HTTPException(status_code=400, detail="Campos numéricos inválidos (valor_credito, juros_mensal, juros_diario).")

    # datas
    dc = parse_date(cliente.get("data_credito"))
    dv = parse_date(cliente.get("data_vencimento"))
    if not dc or not dv:
        raise HTTPException(status_code=400, detail="Datas inválidas. Use YYYY-MM-DD ou DD/MM/YYYY.")
    cliente["data_credito"] = dc.strftime("%Y-%m-%d")
    cliente["data_vencimento"] = dv.strftime("%Y-%m-%d")
    return cliente

def calcular_valores(cliente: dict):
    """
    Valor atualizado = valor_credito + juros_mensal_valor + juros_diario_valor
    - Juros mensal (%): sempre sobre valor_credito
    - Juros diário (%): apenas após o vencimento; conta somente dias úteis; simples (não composto).
      (ex.: 3 dias úteis com 0,5%/dia sobre valor_credito => 0,015 * valor_credito)
    """
    valor_credito = float(cliente.get("valor_credito", 0) or 0)
    juros_mensal = float(cliente.get("juros_mensal", 0) or 0)       # %
    juros_diario = float(cliente.get("juros_diario", 0) or 0)       # % ao dia útil

    # datas
    data_venc = parse_date(cliente.get("data_vencimento"))
    hoje = datetime.now().date()

    # 1) Juros mensal (sempre sobre o valor de crédito)
    juros_mensal_valor = valor_credito * (juros_mensal / 100.0)

    # 2) Juros diário após vencimento (dias úteis)
    dias_uteis_atraso = 0
    juros_diario_valor = 0.0
    if data_venc and hoje > data_venc and juros_diario > 0:
        dias_uteis_atraso = contar_dias_uteis(data_venc, hoje)
        juros_diario_valor = valor_credito * (juros_diario / 100.0) * dias_uteis_atraso

    valor_total = round(valor_credito + juros_mensal_valor + juros_diario_valor, 2)

    # campos de apoio para o frontend
    cliente["juros_mensal_valor"] = round(juros_mensal_valor, 2)
    cliente["juros_diario_valor"] = round(juros_diario_valor, 2)
    cliente["dias_uteis_atraso"] = dias_uteis_atraso
    cliente["valor_total"] = valor_total
    return cliente


# ---------- Rotas ----------

@app.get("/")
def home():
    return {"mensagem": "API LW ativa (modelo oficial: juros mensal + diário em dias úteis)."}

@app.get("/clientes")
def listar_clientes():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        clientes = json.load(f)
    # calcula valores em tempo real (não sobrescreve o arquivo)
    return [calcular_valores(dict(c)) for c in clientes]

@app.post("/cadastrar")
def cadastrar(cliente: dict):
    cliente = validar_cliente(cliente)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    dados.append(cliente)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return {"mensagem": "Cliente cadastrado com sucesso."}

@app.post("/editar/{index}")
def editar(index: int, cliente: dict):
    cliente = validar_cliente(cliente)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if 0 <= index < len(dados):
        dados[index] = cliente
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return {"mensagem": "Cliente atualizado com sucesso."}
    raise HTTPException(status_code=404, detail="Cliente não encontrado.")

@app.delete("/cliente/{index}")
def deletar(index: int):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if 0 <= index < len(dados):
        removido = dados.pop(index)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return {"mensagem": f"Cliente '{removido.get('nome')}' removido com sucesso."}
    raise HTTPException(status_code=404, detail="Cliente não encontrado.")
