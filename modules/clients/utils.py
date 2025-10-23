import os, json
from datetime import datetime
DATA_FILE = os.path.join("data", "clientes.json")
os.makedirs("data", exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

def read_clients():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def write_clients(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calcular_valores(cliente):
    try:
        data_credito = datetime.strptime(cliente.get('data_credito'), "%Y-%m-%d")
    except Exception:
        cliente['dias_corridos'] = 0
        cliente['valor_total'] = cliente.get('valor_base', 0)
        return cliente
    dias = (datetime.now() - data_credito).days
    juros_dia = float(cliente.get('juros_diario', 0))
    valor_base = float(cliente.get('valor_base', 0))
    valor_total = valor_base * ((1 + juros_dia/100) ** max(0, dias))
    cliente['dias_corridos'] = dias
    cliente['valor_total'] = round(valor_total, 2)
    return cliente
