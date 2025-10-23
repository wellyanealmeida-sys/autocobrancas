from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List
import json
import os

app = FastAPI(title="LW Mútuo Mercantil - AutoCobranças")

# 🔓 Permite conexão do front-end (GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois pode restringir para o seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 Caminho do arquivo de dados
DATA_FILE = "data/clientes.json"
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=4, ensure_ascii=False)

# 🧮 Função para atualizar valor com juros diário
def atualizar_valor(cliente):
    data_credito = datetime.strptime(cliente["data_credito"], "%Y-%m-%d")
    dias = (datetime.now() - data_credito).days
    juros_dia = float(cliente["juros_diario"])
    valor_base = float(cliente["valor_base"])

    # cálculo com juros compostos diários
    valor_total = valor_base * ((1 + juros_dia / 100) ** dias)
    cliente["valor_total"] = round(valor_total, 2)
    cliente["dias_corridos"] = dias
    return cliente


# 🏠 Rota principal
@app.get("/")
def home():
    return {"mensagem": "🚀 API da LW Mútuo Mercantil está ativa e rodando!"}


# 🧾 Cadastrar cliente
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
            "juros_mensal": dados.get("juros_mensal"),
            "data_credito": dados.get("data_credito"),
            "objeto_empenho": dados.get("objeto_empenho"),
            "documento": dados.get("documento"),
            "associados": dados.get("associados", []),
        }

        novo_cliente = atualizar_valor(novo_cliente)
        clientes.append(novo_cliente)

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(clientes, f, indent=4, ensure_ascii=False)

        return {"mensagem": "Cliente cadastrado com sucesso!", "cliente": novo_cliente}

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})


# 📊 Listar clientes
@app.get("/clientes")
def listar_clientes():
    try:
        # Garante que o arquivo existe
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            clientes = json.load(f)

        # Se estiver vazio, retorna lista vazia
        if not isinstance(clientes, list):
            clientes = []

        # Atualiza valores de todos os clientes
        clientes_atualizados = [atualizar_valor(c) for c in clientes]

        # Salva os dados atualizados
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(clientes_atualizados, f, indent=4, ensure_ascii=False)

        return JSONResponse(content=clientes_atualizados)

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})
