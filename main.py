from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, date
import json, os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_FILE = "data/clientes.json"
FERIADOS_FIXOS = {(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(12,25)}
FERIADOS_DF_FIXOS = {(4,21),(11,30)}

PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a"  # mesma chave já usada no front
CNPJ_PIX = "59014280000130"  # nova chave CNPJ

def format_date_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")

def format_money_br(v: float) -> str:
    # Formata em "R$ 1.234,56"
    return f"R$ {v:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def calcular_feriados_moveis(ano):
    a = ano % 19; b = ano // 100; c = ano % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    mes = (h + l - 7*m + 114) // 31
    dia = ((h + l - 7*m + 114) % 31) + 1
    pascoa = date(ano, mes, dia)
    return {pascoa - timedelta(days=47), pascoa - timedelta(days=2), pascoa + timedelta(days=60)}

def eh_feriado(d: date):
    return (d.month, d.day) in FERIADOS_FIXOS or (d.month, d.day) in FERIADOS_DF_FIXOS or d in calcular_feriados_moveis(d.year)

def proximo_dia_util(d: date):
    while d.weekday() >= 5 or eh_feriado(d): d += timedelta(days=1)
    return d

def dias_uteis_entre(inicio_exclusive: date, fim_inclusive: date):
    if not inicio_exclusive or not fim_inclusive or fim_inclusive <= inicio_exclusive: return 0
    d = inicio_exclusive + timedelta(days=1); n = 0
    while d <= fim_inclusive:
        if d.weekday() < 5 and not eh_feriado(d): n += 1
        d += timedelta(days=1)
    return n

def parse_date(s):
    try: return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception: return None

def load_clientes():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE,"r",encoding="utf-8") as f:
        try: return json.load(f)
        except Exception: return []

def save_clientes(lst):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(lst,f,ensure_ascii=False,indent=2)

def calcular_vencimentos(dc: date, dv: date|None, limite=3):
    if not dc: return []
    v1 = proximo_dia_util(dv) if dv else proximo_dia_util(dc + timedelta(days=30))
    vencs = [v1]
    while len(vencs) < limite: vencs.append(proximo_dia_util(vencs[-1] + timedelta(days=30)))
    return vencs

def validar_cliente(cli: dict):
    for c in ["nome","valor_credito","juros_mensal","telefone"]:
        if str(cli.get(c,"")).strip() == "": raise HTTPException(400, f"O campo '{c}' é obrigatório.")
    tel = cli.get("telefone","").replace("+","").replace(" ","").replace("-","")
    if not tel.isdigit() or len(tel) < 10: raise HTTPException(400,"Telefone inválido. Use 5561XXXXXXXX.")
    cli["telefone"] = tel
    try:
        cli["valor_credito"] = float(cli["valor_credito"]); cli["juros_mensal"] = float(cli["juros_mensal"])
    except Exception: raise HTTPException(400,"Valor de crédito ou juros mensal inválido.")
    jd = cli.get("juros_diario_valor", cli.get("juros_diario", 0))
    try: cli["juros_diario_valor"] = float(jd or 0.0)
    except Exception: raise HTTPException(400,"Juros diário inválido (use apenas números).")
    dc = parse_date(cli.get("data_credito"))
    if not dc:
        dc = datetime.now().date(); cli["data_credito"] = dc.strftime("%Y-%m-%d")
    dv = parse_date(cli.get("data_vencimento"))
    if dv:
        dv = proximo_dia_util(dv); cli["data_vencimento"] = dv.strftime("%Y-%m-%d")
    assoc = cli.get("associados", [])
    if isinstance(assoc,str): assoc = [s.strip() for s in assoc.split(",") if s.strip()]
    elif isinstance(assoc,list): assoc = [str(s).strip() for s in assoc if str(s).strip()]
    else: assoc = []
    cli["associados"] = assoc
    status = (cli.get("status") or "ativo").lower().strip()
    if status not in ["ativo","quitado","inadimplente"]: status = "ativo"
    cli["status"] = status
    if "ultimo_envio" in cli and cli["ultimo_envio"]:
        try: datetime.fromisoformat(cli["ultimo_envio"])
        except Exception: cli["ultimo_envio"] = None
    else: cli["ultimo_envio"] = None
    return cli

def calcular_ciclos(cli: dict):
    hoje = datetime.now().date()
    valor_credito = float(cli.get("valor_credito",0) or 0)
    juros_mensal = float(cli.get("juros_mensal",0) or 0)
    jd_r = float(cli.get("juros_diario_valor",0) or 0)
    dc = parse_date(cli.get("data_credito")); dv = parse_date(cli.get("data_vencimento"))
    vencs = calcular_vencimentos(dc, dv, limite=3)
    ciclos, base = [], valor_credito
    for i, v in enumerate(vencs):
        jm = base * (juros_mensal/100.0)
        prox = vencs[i+1] if i+1 < len(vencs) else hoje
        fim = min(hoje, prox)
        du = jd_total = 0
        if fim > v:
            du = dias_uteis_entre(v, fim)   # 1 dia útil após o vencimento, só dias úteis
            jd_total = jd_r * max(0, du)
        valor_ciclo = base + jm + jd_total
        ciclos.append({"vencimento": v.strftime("%Y-%m-%d"),
                       "juros_mensal_valor": round(jm,2),
                       "dias_uteis": du,
                       "juros_diario_total": round(jd_total,2),
                       "valor_atualizado": round(valor_ciclo,2)})
        base = valor_ciclo
    meses_atraso = sum(1 for v in vencs if hoje > v)
    status = cli.get("status","ativo")
    if meses_atraso >= 3: status = "inadimplente"
    venc_atual = None
    for v in vencs:
        if hoje <= v: venc_atual = v; break
    if not venc_atual and vencs: venc_atual = vencs[-1]
    return {"vencimentos":[d.strftime("%Y-%m-%d") for d in vencs],
            "ciclos": ciclos,
            "status": status,
            "vencimento_atual": venc_atual.strftime("%Y-%m-%d") if venc_atual else cli.get("data_vencimento"),
            "valor_total": round(base,2)}

def aplicar_calculo(cli: dict):
    cli.update(calcular_ciclos(cli)); return cli

@app.get("/cobrancas/hoje")
def cobrancas_hoje():
    # Carrega e recalcula todos os clientes
    lst = load_clientes()
    for c in lst:
        aplicar_calculo(c)
    save_clientes(lst)

    hoje_iso = datetime.now().date().strftime("%Y-%m-%d")
    cobrancas = []

    for i, cli in enumerate(lst):
        # Só quem vence HOJE
        if cli.get("vencimento_atual") != hoje_iso:
            continue

        status = (cli.get("status") or "ativo").lower()
        # Não envia para quitado
        if status == "quitado":
            continue

        ciclos = cli.get("ciclos") or []
        ciclo_atual = next(
            (ci for ci in ciclos if ci.get("vencimento") == cli.get("vencimento_atual")),
            None
        )
        if not ciclo_atual and ciclos:
            ciclo_atual = ciclos[-1]

        valor = float(
            ciclo_atual.get("valor_atualizado")
            if ciclo_atual else cli.get("valor_credito", 0.0)
        )

        # Data em dd/mm/aaaa
        dt_venc = datetime.strptime(cli["vencimento_atual"], "%Y-%m-%d").date()
        data_venc_br = format_date_br(dt_venc)

        objeto = cli.get("objeto") or ""

        # MONTA A MENSAGEM (sem valor de crédito, só valor atualizado)
        msg_partes = []
        msg_partes.append(f"Olá {cli.get('nome','')}, tudo bem?\n\n")
        msg_partes.append("Aqui é da LW Mútuo Mercantil.\n\n")
        texto_contrato = f"Estamos lembrando que hoje, dia {data_venc_br}, vence o pagamento referente ao seu contrato."
        if objeto:
            texto_contrato += f" Objeto em garantia: {objeto}."
        msg_partes.append(texto_contrato + "\n\n")
        msg_partes.append(
            f"Valor para pagamento hoje (com juros do mês e juros diário conforme combinado): {format_money_br(valor)}.\n\n"
        )
        msg_partes.append("Chaves PIX para pagamento:\n")
        msg_partes.append(f"• Chave padrão: {PIX_KEY}\n")
        msg_partes.append(f"• CNPJ: {CNPJ_PIX}\n\n")
        msg_partes.append(
            "Após o pagamento, por favor envie o comprovante neste número para atualização do sistema.\n\n"
        )
        msg_partes.append("Qualquer dúvida, estamos à disposição.")
        mensagem = "".join(msg_partes)

        cobrancas.append({
            "indice": i,  # índice do cliente no arquivo
            "nome": cli.get("nome"),
            "telefone": cli.get("telefone"),
            "data_vencimento": data_venc_br,
            "valor_com_juros": valor,
            "mensagem_whatsapp": mensagem,
            "status": status,
        })

    return cobrancas

@app.get("/clientes")
def listar_clientes():
    lst = load_clientes()
    for c in lst: aplicar_calculo(c)
    save_clientes(lst); return lst

@app.post("/cadastrar")
def cadastrar_cliente(cli: dict):
    cli = validar_cliente(cli); lst = load_clientes(); lst.append(cli); save_clientes(lst); return {"ok": True}

@app.post("/editar/{i}")
def editar_cliente(i: int, cli: dict):
    lst = load_clientes()
    if i < 0 or i >= len(lst): raise HTTPException(404,"Cliente não encontrado.")
    cli = validar_cliente(cli); lst[i] = cli; save_clientes(lst); return {"ok": True}

@app.post("/quitar/{i}")
def quitar_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst): raise HTTPException(404,"Cliente não encontrado.")
    lst[i]["status"] = "quitado"; save_clientes(lst); return {"ok": True}

@app.post("/reativar/{i}")
def reativar_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst): raise HTTPException(404,"Cliente não encontrado.")
    lst[i]["status"] = "ativo"; save_clientes(lst); return {"ok": True}

@app.post("/excluir/{i}")
def excluir_cliente(i: int):
    lst = load_clientes()
    if i < 0 or i >= len(lst): raise HTTPException(404,"Cliente não encontrado.")
    del lst[i]; save_clientes(lst); return {"ok": True}

@app.get("/")
def root(): return {"status":"LW Mútuo Mercantil API v3.3 Render 🚀"}
