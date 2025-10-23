from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os
from datetime import datetime

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças")

# Configuração CORS (permite acesso do GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join("data", "clientes.json")

# Cria pasta e arquivo, se não existir
if not os.path.exists(DATA_FILE):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


# Função auxiliar: calcular juros e valor atualizado
def calcular_valor(cliente):
    try:
        data_credito = datetime.strptime(cliente.get("data_credito", ""), "%Y-%m-%d")
    except Exception:
        cliente["dias_corridos"] = 0
        cliente["valor_total"] = cliente.get("valor_base", 0)
        return cliente

    dias = (datetime.now() - data_credito).days
    if dias < 0:
        dias = 0

    juros_diario = float(cliente.get("juros_diario", 0))
    valor_base = float(cliente.get("valor_base", 0))
    valor_total = valor_base * ((1 + juros_diario / 100) ** dias)
    juros_mes = round(juros_diario * 30, 2)

    cliente["dias_corridos"] = dias
    cliente["valor_total"] = round(valor_total, 2)
    cliente["juros_mes"] = juros_mes
    return cliente


# Página inicial da API
@app.get("/")
def home():
    return {"mensagem": "API LW Mútuo Mercantil ativa."}


# Listar todos os clientes
@app.get("/clientes")
def listar_clientes():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        clientes = json.load(f)
    for c in clientes:
        calcular_valor(c)
    return clientes


# Função para validar dados obrigatórios
def validar_cliente(cliente: dict):
    obrigatorios = ["nome", "data_credito", "valor_base", "telefone"]
    for campo in obrigatorios:
        valor = str(cliente.get(campo, "")).strip()
        if not valor:
            raise HTTPException(status_code=400, detail=f"O campo '{campo}' é obrigatório.")
    # Valida formato do telefone (precisa começar com DDI, ex: 5561...)
    telefone = cliente["telefone"].replace("+", "").replace(" ", "").replace("-", "")
    if not telefone.isdigit() or len(telefone) < 10:
        raise HTTPException(status_code=400, detail="Número de telefone inválido. Use o formato 5561XXXXXXXXX.")
    cliente["telefone"] = telefone
    return cliente


# Cadastrar novo cliente
@app.post("/cadastrar")
def cadastrar_cliente(cliente: dict):
    cliente = validar_cliente(cliente)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    dados.append(cliente)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return {"mensagem": "Cliente cadastrado com sucesso."}


# Editar cliente existente
@app.post("/editar/{index}")
def editar_cliente(index: int, cliente: dict):
    cliente = validar_cliente(cliente)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if 0 <= index < len(dados):
        dados[index] = cliente
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return {"mensagem": "Cliente atualizado com sucesso."}
    raise HTTPException(status_code=404, detail="Cliente não encontrado.")


# Excluir cliente
@app.delete("/cliente/{index}")
def excluir_cliente(index: int):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if 0 <= index < len(dados):
        removido = dados.pop(index)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return {"mensagem": f"Cliente '{removido.get('nome')}' removido com sucesso."}
    raise HTTPException(status_code=404, detail="Cliente não encontrado.")
