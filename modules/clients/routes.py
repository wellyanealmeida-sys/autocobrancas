from fastapi import APIRouter, Request, HTTPException
from .utils import read_clients, write_clients, calcular_valores

router = APIRouter()

@router.get("/clientes")
def listar_clientes():
    clientes = read_clients()
    clientes = [calcular_valores(c) for c in clientes]
    write_clients(clientes)
    return clientes

@router.post("/cadastrar")
async def cadastrar(request: Request):
    data = await request.json()
    clientes = read_clients()
    associados = data.get('associados') or []
    if isinstance(associados, str):
        associados = [a.strip() for a in associados.split(',') if a.strip()]
    novo = {
        "nome": data.get('nome'),
        "valor_base": float(data.get('valor_base') or 0),
        "juros_diario": float(data.get('juros_diario') or 0),
        "juros_mensal": float(data.get('juros_mensal') or 0),
        "data_credito": data.get('data_credito'),
        "objeto_empenho": data.get('objeto_empenho'),
        "documento": data.get('documento'),
        "associados": associados,
        "telefone": data.get('telefone') or data.get('telefone_whats') or data.get('telefone_cliente')
    }
    novo = calcular_valores(novo)
    clientes.append(novo)
    write_clients(clientes)
    return {"mensagem":"Cadastrado","cliente":novo}

@router.post("/editar/{index}")
async def editar(index: int, request: Request):
    data = await request.json()
    clientes = read_clients()
    if index < 0 or index >= len(clientes):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for k in ['nome','valor_base','juros_diario','juros_mensal','data_credito','objeto_empenho','documento','associados','telefone']:
        if k in data:
            clientes[index][k] = data[k]
    clientes[index] = calcular_valores(clientes[index])
    write_clients(clientes)
    return {"mensagem":"Atualizado","cliente":clientes[index]}

@router.delete("/cliente/{index}")
def deletar(index: int):
    clientes = read_clients()
    if index < 0 or index >= len(clientes):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    removed = clientes.pop(index)
    write_clients(clientes)
    return {"mensagem":"Removido","cliente":removed}
