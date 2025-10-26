from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os, base64, requests
from datetime import datetime, timedelta, timezone

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças (GitHub persist, último envio)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Feriados nacionais e DF (exemplos; pode ampliar) ---
FERIADOS_FIXOS = {(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(12,25)}  # nacionais fixos (dia, mês)
FERIADOS_MOVELS_POR_ANO = {}  # opcional (Carnaval, Páscoa, Corpus Christi etc.) — pode preencher depois
FERIADOS_DF_FIXOS = {(4,21)}  # Fundação de Brasília (já nacional) e 11/30 (Dia do Evangélico-DF)
FERIADOS_DF_DATAS = {(11,30)}  # Dia do Evangélico no DF

# -------- Config GitHub persist --------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "wellyanealmeida-sys").strip()
GITHUB_REPO  = os.getenv("GITHUB_REPO",  "autocobrancas").strip()
GITHUB_PATH  = "data/clientes.json"

# Local fallback
DATA_FILE = os.path.join("data", "clientes.json")
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# -------- Utils datas/dias úteis --------
def parse_date(s: str):
    if not s or s == "undefined": return None
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
        if d.weekday() < 5:  # seg..sex
            dias += 1
        d += timedelta(days=1)
    return dias

def eh_feriado(d):
    # nacionais fixos
    if (d.month, d.day) in FERIADOS_FIXOS:
        return True
    # DF fixos
    if (d.month, d.day) in FERIADOS_DF_DATAS:
        return True
    # móveis por ano (se quiser popular futuramente)
    if d.year in FERIADOS_MOVELS_POR_ANO and d in FERIADOS_MOVELS_POR_ANO[d.year]:
        return True
    return False

def proximo_dia_util(d):
    # avança se cair fim de semana/feriado
    while d.weekday() >= 5 or eh_feriado(d):
        d += timedelta(days=1)
    return d

def calcular_vencimentos(data_credito, limite=3):
    """Gera até 3 vencimentos mensais (30 dias a partir do crédito), ajustados p/ dia útil."""
    vencs = []
    if not data_credito:
        return vencs
    d = data_credito
    for _ in range(limite):
        d = d + timedelta(days=30)
        d = proximo_dia_util(d)
        vencs.append(d)
    return vencs

def dias_uteis_entre(inicio_exclusive, fim_inclusive):
    """Conta dias úteis no intervalo (inicio_exclusive, fim_inclusive]."""
    if not inicio_exclusive or not fim_inclusive or fim_inclusive <= inicio_exclusive:
        return 0
    d = inicio_exclusive + timedelta(days=1)
    n = 0
    while d <= fim_inclusive:
        if d.weekday() < 5 and not eh_feriado(d):
            n += 1
        d += timedelta(days=1)
    return n

# -------- Persistência: GitHub Contents API --------
def gh_headers():
    return {"Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"}

def gh_get_file():
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_PATH}"
    r = requests.get(url, headers=gh_headers(), timeout=20)
    if r.status_code == 200:
        b64 = r.json()["content"]
        sha = r.json()["sha"]
        data = base64.b64decode(b64).decode("utf-8")
        return data, sha
    return None, None

def gh_put_file(text, sha=None, message="Atualiza clientes.json"):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_PATH}"
    payload = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise HTTPException(500, f"Falha ao salvar no GitHub: {r.status_code} {r.text}")

def _load():
    # 1) tenta GitHub
    if GITHUB_TOKEN:
        try:
            txt, _ = gh_get_file()
            if txt is not None:
                return json.loads(txt)
        except Exception:
            pass
    # 2) fallback local
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(arr, message="Atualiza clientes.json"):
    txt = json.dumps(arr, ensure_ascii=False, indent=2)
    if GITHUB_TOKEN:
        try:
            _, sha = gh_get_file()
            gh_put_file(txt, sha, message)
            return
        except Exception:
            pass
    # fallback local
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(txt)

# -------- Validação / Cálculo --------
def calcular_valores(cli: dict):
    valor_credito = float(cli.get("valor_credito", 0) or 0)
    juros_mensal  = float(cli.get("juros_mensal", 0) or 0)              # %
    jd_r          = float(cli.get("juros_diario_valor", 0) or 0)        # R$/dia útil

    dc = parse_date(cli.get("data_credito"))
    dv = parse_date(cli.get("data_vencimento"))  # pode vir preenchido; se faltar, calculamos
    hoje = datetime.now().date()

    # 1) Vencimentos inteligentes (até 3 ciclos)
    vencs = calcular_vencimentos(dc, limite=3)
    # Se o cliente preencheu manualmente o 1º vencimento, honramos; ajusta p/ útil:
    if dv:
        vencs[0] = proximo_dia_util(dv)

    # 2) Acúmulo progressivo: aplica juro mensal na virada de cada vencimento ultrapassado
    # e soma juros diários (R$ fixo) por dias úteis em cada intervalo após cada vencimento.
    valor_base = valor_credito
    juros_mensal_total = 0.0
    juros_diario_total = 0.0
    dias_uteis_total = 0
    meses_atraso = 0

    # iteramos cada ciclo: [v1, v2, v3]
    anterior = dc
    for idx, v in enumerate(vencs, start=1):
        # se ainda não chegou no 1º vencimento, não há atraso
        if hoje <= v:
            break

        # no dia do vencimento, aplica juro mensal sobre a base até então
        jm_val = valor_base * (juros_mensal / 100.0)
        juros_mensal_total += jm_val
        valor_base += jm_val  # base cresce com juro mensal do ciclo

        # dias úteis de atraso deste ciclo: (v, hoje] ou até o próximo vencimento, se não chegou nele ainda
        # se já passou para o próximo ciclo, só conta até o próximo vencimento; senão, até hoje
        fim_ciclo = min(hoje, vencs[idx] if idx < len(vencs) else hoje)
        du = dias_uteis_entre(v, fim_ciclo)
        dias_uteis_total += du
        juros_diario_total += jd_r * du

        # se hoje já passou deste vencimento, consideramos 1 mês de atraso concluído
        if hoje > v:
            meses_atraso += 1

    # 3) Valor total
    valor_total = round(valor_base + juros_diario_total, 2)

    # 4) Status especial: 3 meses → inadimplente
    status_atual = cli.get("status", "ativo")
    if meses_atraso >= 3:
        status_atual = "inadimplente"

    # 5) Seta campos de exibição
    cli["juros_mensal_valor"] = round(juros_mensal_total, 2)
    cli["juros_diario_valor_dia"] = round(jd_r, 2)
    cli["juros_diario_total"] = round(juros_diario_total, 2)
    cli["dias_uteis_atraso"] = dias_uteis_total
    cli["valor_total"] = valor_total
    cli["status"] = status_atual
    cli["vencimentos"] = [d.strftime("%Y-%m-%d") for d in vencs]
    # Para exibição "atual": usamos o vencimento mais próximo ainda não alcançado, ou o último
    cli["vencimento_atual"] = next((d for d in vencs if hoje <= parse_date(d)), vencs[-1]).strftime("%Y-%m-%d") if vencs else cli.get("data_vencimento")
    return cli


# -------- Rotas --------
@app.get("/")
def home():
    return {"msg": "API LW ativa (GitHub persist, dias úteis, último envio)."}

@app.get("/clientes")
def clientes():
    arr = _load()
    return [calcular_valores(dict(c)) for c in arr]

@app.post("/cadastrar")
def cadastrar(cli: dict):
    cli = validar_cliente(cli)
    arr = _load()
    arr.append(cli)
    _save(arr, "Cadastro de cliente")
    return {"mensagem": "Cliente cadastrado."}

@app.post("/editar/{i}")
def editar(i: int, cli: dict):
    cli = validar_cliente(cli)
    arr = _load()
    if 0 <= i < len(arr):
        if "ultimo_envio" not in cli:
            cli["ultimo_envio"] = arr[i].get("ultimo_envio")
        if "status" not in cli:
            cli["status"] = arr[i].get("status", "ativo")
        arr[i] = cli
        _save(arr, f"Edita cliente #{i}")
        return {"mensagem": "Cliente atualizado."}
    raise HTTPException(404, "Cliente não encontrado.")

@app.delete("/cliente/{i}")
def excluir(i: int):
    arr = _load()
    if 0 <= i < len(arr):
        rm = arr.pop(i)
        _save(arr, f"Exclui cliente #{i} ({rm.get('nome')})")
        return {"mensagem": f"Cliente '{rm.get('nome')}' removido."}
    raise HTTPException(404, "Cliente não encontrado.")

@app.post("/quitar/{i}")
def quitar(i: int):
    arr = _load()
    if 0 <= i < len(arr):
        arr[i]["status"] = "quitado"
        _save(arr, f"Quita cliente #{i}")
        return {"mensagem": f"Cliente '{arr[i].get('nome')}' quitado."}
    raise HTTPException(404, "Cliente não encontrado.")

@app.post("/reativar/{i}")
def reativar(i: int):
    arr = _load()
    if 0 <= i < len(arr):
        arr[i]["status"] = "ativo"
        _save(arr, f"Reativa cliente #{i}")
        return {"mensagem": f"Cliente '{arr[i].get('nome')}' reativado."}
    raise HTTPException(404, "Cliente não encontrado.")

@app.post("/registrar_envio/{i}")
def registrar_envio(i: int):
    """Marca data/hora do último envio de cobrança."""
    arr = _load()
    if 0 <= i < len(arr):
        arr[i]["ultimo_envio"] = datetime.now(timezone.utc).isoformat()
        _save(arr, f"Registra último envio cliente #{i}")
        return {"mensagem": "Último envio registrado."}
    raise HTTPException(404, "Cliente não encontrado.")
