import json, os
from datetime import datetime

DATA_DIR = "data"
CLIENTES_FILE = os.path.join(DATA_DIR, "clientes.json")
COBRANCAS_FILE = os.path.join(DATA_DIR, "cobrancas.json")

def calcular_juros(valor_base, juros_diario, dias_atraso):
    return round(valor_base * (1 + (juros_diario / 100) * dias_atraso), 2)

def atualizar_cobrancas():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with open(CLIENTES_FILE, "r", encoding="utf-8") as f:
        clientes = json.load(f)
    cobrancas = []
    for cliente in clientes:
        data_emprestimo = datetime.strptime(cliente["data_emprestimo"], "%Y-%m-%d")
        dias = (datetime.now() - data_emprestimo).days
        valor_atualizado = calcular_juros(cliente["valor_base"], cliente["juros_diario"], dias)
        cobrancas.append({
            "nome": cliente["nome"],
            "associado": cliente.get("associado", ""),
            "documento": cliente.get("documento", ""),
            "objeto_empenho": cliente.get("objeto_empenho", ""),
            "valor_base": cliente["valor_base"],
            "juros_diario": cliente["juros_diario"],
            "dias": dias,
            "valor_atualizado": valor_atualizado,
            "whatsapp": f"https://wa.me/{cliente['telefone']}?text=Olá%20{cliente['nome']}!%20Sua%20cobrança%20atualizada%20é%20de%20R${valor_atualizado}"
        })
    with open(COBRANCAS_FILE, "w", encoding="utf-8") as f:
        json.dump(cobrancas, f, ensure_ascii=False, indent=2)
    print("Cobranças atualizadas com sucesso:", hoje)

if __name__ == "__main__":
    atualizar_cobrancas()
