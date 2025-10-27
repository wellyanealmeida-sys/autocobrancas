from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, date
import json, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data/clientes.json"

def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def load_clientes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_clientes(lst):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)

# FERIADOS (fixos + DF + móveis)
FERIADOS_FIXOS = {(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(12,25)}
FERIADOS_DF_FIXOS = {(4,21),(11,30)}

def calcular_feriados_moveis(ano):
    # Gauss
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    pascoa = date(ano, mes, dia)
    return {pascoa - timedelta(days=47), pascoa - timedelta(days=2), pascoa + timedelta(days=60)}

def eh_feriado(d: date):
    if (d.month, d.day) in FERIADOS_FIXOS or (d.month, d.day) in FERIADOS_DF_FIXOS:
        return True
    if d in calcular_feriados_moveis(d.year):
        return True
    return False

def proximo_dia_util(d: date):
    while d.weekday() >= 5 or eh_feriado(d):
        d += timedelta(days=1)
    return d

def dias_uteis_entre(inicio_exclusive, fim_inclusive):
    if not inicio_exclusive or not fim_inclusive or fim_inclusive <= inicio_exclusive:
        return 0
    d = inicio_exclusive + timedelta(days=1)
    n = 0
    while d <= fim_inclusive:
        if d.weekday() < 5 and not eh_feriado(d):
            n += 1
        d += timedelta(days=1)
    return n

def calcular_vencimentos(data_credito, limite=3):
    vencs = []
    if not data_credito:
        return vencs
    d = data_credito
    for _ in range(limite):
        d = proximo_dia_util(d + timedelta(days=30))
        vencs.append(d)
    return vencs

def validar_cliente(cli: dict):
    obrig = ["nome", "valor_credito", "juros_mensal", "telefone"]
    for c in obrig:
        if str(cli.get(c, "")).strip() == "":
            raise HTTPException(400, f"O campo '{c}' é obrigatório.")

    tel = cli.get("telefone", "").replace("+", "").replace(" ", "").replace("-", "")
    if not tel.isdigit() or len(tel) < 10:
        raise HTTPException(400, "Telefone inválido. Use 5561XXXXXXXX.")
    cli["telefone"] = tel

    try:
        cli["valor_credito"] = float(cli["valor_credito"])
        cli["juros_mensal"] = float(cli["juros_mensal"])
    except Exception:
        raise HTTPException(400, "Valor de crédito ou juros mensal inválido.")

    jd_val = cli.get("juros_diario_valor", cli.get("juros_diario", 0))
    try:
        cli["juros_diario_valor"] = float(jd_val or 0.0)
    except Exception:
        raise HTTPException(400, "Juros diário inválido (use apenas números)." )

    dc = parse_date(cli.get("data_credito"))
    if not dc:
        dc = datetime.now().date()
        cli["data_credito"] = dc.strftime("%Y-%m-%d")

    dv = parse_date(cli.get("data_vencimento"))
    if not dv:
        dv = proximo_dia_util(dc + timedelta(days=30))
        cli["data_vencimento"] = dv.strftime("%Y-%m-%d")
    else:
        dv = proximo_dia_util(dv)
        cli["data_vencimento"] = dv.strftime("%Y-%m-%d")

    assoc = cli.get("associados", [])
    if isinstance(assoc, str):
        assoc = [s.strip() for s in assoc.split(",") if s.strip()]
    elif isinstance(assoc, list):
        assoc = [str(s).strip() for s in assoc if str(s).strip()]
    else:
        assoc = []
    cli["associados"] = assoc

    status = (cli.get("status") or "ativo").lower().strip()
    if status not in ["ativo", "quitado", "inadimplente"]:
        status = "ativo"
    cli["status"] = status

    if "ultimo_envio" in cli and cli["ultimo_envio"]:
        try:
            datetime.fromisoformat(cli["ultimo_envio"])
        except Exception:
            cli["ultimo_envio"] = None
    else:
        cli["ultimo_envio"] = None

    return cli

def calcular_valores(cli: dict):
    valor_credito = float(cli.get("valor_credito", 0) or 0)
    juros_mensal = float(cli.get("juros_mensal", 0) or 0)
    jd_r = float(cli.get("juros_diario_valor", 0) or 0)

    dc = parse_date(cli.get("data_credito"))
    dv = parse_date(cli.get("data_vencimento"))
    hoje = datetime.now().date()

    vencs = calcular_vencimentos(dc, limite=3)
    if dv:
        vencs[0] = proximo_dia_util(dv)

    valor_base = valor_credito
    juros_mensal_total = 0.0
    juros_diario_total = 0.0
    dias_uteis_total = 0
    meses_atraso = 0

    for idx, v in enumerate(vencs, start=1):
        if hoje <= v:
            break
        jm_val = valor_base * (juros_mensal / 100.0)
        juros_mensal_total += jm_val
        valor_base += jm_val
        fim_ciclo = min(hoje, vencs[idx] if idx < len(vencs) else hoje)
        du = dias_uteis_entre(v, fim_ciclo)
        dias_uteis_total += du
        juros_diario_total += jd_r * du
        if hoje > v:
            meses_atraso += 1

    valor_total = round(valor_base + juros_diario_total, 2)
    status_atual = cli.get("status", "ativo")
    if meses_atraso >= 3:
        status_atual = "inadimplente"

    cli["juros_mensal_valor"] = round(juros_mensal_total, 2)
    cli["juros_diario_valor_dia"] = round(jd_r, 2)
    cli["juros_diario_total"] = round(juros_diario_total, 2)
    cli["dias_uteis_atraso"] = dias_uteis_total
    cli["valor_total"] = valor_total
    cli["status"] = status_atual
    cli["vencimentos"] = [d.strftime("%Y-%m-%d") for d in vencs]
    cli["vencimento_atual"] = next((d for d in vencs if hoje <= d), vencs[-1]).strftime("%Y-%m-%d") if vencs else cli.get("data_vencimento")
    return cli

@app.get("/clientes")
def listar_clientes():
    lst = load_clientes()
    for c in lst:
        calcular_valores(c)
    save_clientes(lst)
    return lst

@app.post("/cadastrar")
def cadastrar_cliente(cli: dict):
    cli = validar_cliente(cli)
    lst = load_clientes()
    lst.append(cli)
    save_clientes(lst)
    return {"ok": True, "msg": "Cliente cadastrado com sucesso."}

@app.post("/editar/{i}")
def editar_cliente(i: int, cli: dict):
    lst = load_clientes()
    if i < 0 or i >= len(lst):
        raise HTTPException(404, "Cliente não encontrado.")
    cli = validar_cliente(cli)
    lst[i] = cli
    save_clientes(lst)
    return {"ok": True}

@app.post("/quitar/{i}")
def quitar_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst):
        raise HTTPException(404, "Cliente não encontrado.")
    lst[i]["status"] = "quitado"
    save_clientes(lst)
    return {"ok": True}

@app.post("/reativar/{i}")
def reativar_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst):
        raise HTTPException(404, "Cliente não encontrado.")
    lst[i]["status"] = "ativo"
    save_clientes(lst)
    return {"ok": True}

@app.post("/excluir/{i}")
def excluir_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst):
        raise HTTPException(404, "Cliente não encontrado.")
    del lst[i]
    save_clientes(lst)
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "LW Mútuo Mercantil API rodando corretamente 🚀"}
