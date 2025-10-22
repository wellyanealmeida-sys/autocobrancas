from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json
import os

app = FastAPI()

# 🔓 Permite que o front-end do GitHub Pages se comunique com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou ["https://wellyanealmeida-sys.github.io"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 Caminho onde os dados serão salvos
DATA_FILE = "data/clientes.json"

# 🔧 Garante que o arquivo exista
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=4, ensure_ascii=False)


# 🏠 Rota inicial
@app.get("/")
def home():
    return {"mensagem": "🚀 API da LW Mútuo Mercantil está rodando!"}


# 🧮 Função para atualizar juros diários
def atualizar_valor(cliente):
    data_emprestimo = datetime.strptime(cliente["data_emprestimo"], "%Y-%m-%d")
    dias = (datetime.now() - data_emprestimo).days
    juros_dia = float(cliente["juros_diario"])
    valor_base = float(cliente["valor_base"])
    valor_total = valor_base * ((1 + juros_dia / 100) ** dias)
    cliente["valor_total"] = round(valor_total, 2)
    cliente["dias_corridos"] = dias
    return cliente


# 🧾 Rota para cadastrar novo cliente
@app.post("/cadastrar")
async def cadastrar(request: Request):
    try:
        dados = await request.json()

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            clientes = json.load(f)

        novo_cliente = {
            "nome": dados.get("nome"),
            "valor_base": dados.get("valor_base"),
            "juros_diario": dados.get("juros_diario"),
            "data_emprestimo": dados.get("data_emprestimo"),
            "objeto_empenho": dados.get("objeto_empenho"),
            "documento": dados.get("documento"),
            "associados": dados.get("associados"),
        }

        novo_cliente = atualizar_valor(novo_cliente)
        clientes.append(novo_cliente)

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(clientes, f, indent=4, ensure_ascii=False)

        return {"mensagem": "Cliente cadastrado com sucesso!", "cliente": novo_cliente}

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})


# 📊 Rota para listar clientes com valores atualizados
@app.get("/clientes")
def listar_clientes():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        clientes = json.load(f)

    clientes_atualizados = [atualizar_valor(c) for c in clientes]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clientes_atualizados, f, indent=4, ensure_ascii=False)

    return clientes_atualizados
