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
def validar_cliente(cli: dict):
    obrig = ["nome","valor_credito","data_credito","data_vencimento","juros_mensal","telefone"]
    for c in obrig:
        if str(cli.get(c,"")).strip() == "":
            raise HTTPException(400, f"O campo '{c}' é obrigatório.")

    tel = cli.get("telefone","").replace("+","").replace(" ","").replace("-","")
    if not tel.isdigit() or len(tel) < 10:
        raise HTTPException(400, "Telefone inválido. Use 5561XXXXXXXX.")
    cli["telefone"] = tel

    try:
        cli["valor_credito"] = float(cli["valor_credito"])
        cli["juros_mensal"]  = float(cli["juros_mensal"])  # %
    except Exception:
        raise HTTPException(400, "valor_credito/juros_mensal inválidos.")

    # Juros diário em R$/dia útil (compat aceita 'juros_diario')
    jd_val = cli.get("juros_diario_valor", cli.get("juros_diario", 0))
    try:
        cli["juros_diario_valor"] = float(jd_val or 0.0)
    except Exception:
        raise HTTPException(400, "juros_diario_valor inválido (R$ por dia útil).")

    # Datas
    dc = parse_date(cli.get("data_credito"))
    dv = parse_date(cli.get("data_vencimento"))
    if not dc or not dv:
        raise HTTPException(400, "Datas inválidas. Use YYYY-MM-DD ou DD/MM/YYYY.")
    cli["data_credito"] = dc.strftime("%Y-%m-%d")
    cli["data_vencimento"] = dv.strftime("%Y-%m-%d")

    # Normaliza associados: lista de strings
    assoc = cli.get("associados", [])
    if isinstance(assoc, str):
        assoc = [s.strip() for s in assoc.split(",") if s.strip()]
    elif isinstance(assoc, list):
        assoc = [str(s).strip() for s in assoc if str(s).strip()]
    else:
        assoc = []
    cli["associados"] = assoc

    status = (cli.get("status") or "ativo").lower().strip()
    cli["status"] = "quitado" if status == "quitado" else "ativo"

    # mantém último envio se vier
    if "ultimo_envio" in cli and cli["ultimo_envio"]:
        try:
            datetime.fromisoformat(cli["ultimo_envio"])
        except Exception:
            cli["ultimo_envio"] = None
    else:
        cli["ultimo_envio"] = cli.get("ultimo_envio", None)

    return cli

def calcular_valores(cli: dict):
    valor_credito = float(cli.get("valor_credito", 0) or 0)
    juros_mensal  = float(cli.get("juros_mensal", 0) or 0)              # %
    jd_r          = float(cli.get("juros_diario_valor", 0) or 0)        # R$/dia útil

    venc = parse_date(cli.get("data_vencimento"))
    hoje = datetime.now().date()

    juros_mensal_valor = valor_credito * (juros_mensal / 100.0)

    dias_atraso = 0
    juros_diario_total = 0.0
    if cli.get("status","ativo") == "ativo":
        dias_atraso = dias_uteis_apos_vencimento(venc, hoje)
        juros_diario_total = jd_r * dias_atraso

    valor_total = round(valor_credito + juros_mensal_valor + juros_diario_total, 2)

    cli["juros_mensal_valor"] = round(juros_mensal_valor, 2)
    cli["juros_diario_valor_dia"] = round(jd_r, 2)
    cli["juros_diario_total"] = round(juros_diario_total, 2)
    cli["dias_uteis_atraso"] = dias_atraso
    cli["valor_total"] = valor_total
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
