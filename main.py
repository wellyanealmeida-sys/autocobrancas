
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "database.db"

def get_db():
    return sqlite3.connect(DB)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefone TEXT,
        valor REAL,
        data_credito TEXT,
        primeiro_vencimento TEXT,
        dias INTEGER,
        juros REAL,
        associados TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.post("/cadastrar")
def cadastrar(d: dict):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO clientes
        (nome, telefone, valor, data_credito, primeiro_vencimento, dias, juros, associados)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            d["nome"], d["telefone"], d["valor"],
            d["data_credito"], d["primeiro_vencimento"],
            d["dias"], d["juros"], d["associados"]
        )
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/clientes")
def listar():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM clientes").fetchall()
    conn.close()
    keys = ["id","nome","telefone","valor","data_credito","primeiro_vencimento","dias","juros","associados"]
    return [dict(zip(keys, r)) for r in rows]
