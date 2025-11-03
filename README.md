# LW Mútuo Mercantil — Sistema de Cobranças Automáticas (v3.3 Render)

- Vencimentos em sequência (1º,2º,3º)
- Juros mensal no vencimento + juros diário 1 dia útil após vencimento (feriados BR+DF)
- WhatsApp com resumo por ciclo
- Actions diário (09:00 BRT) atualiza data/clientes.json
- Frontend aponta para https://autocobrancas.onrender.com

## Rodar local
pip install -r requirements.txt
uvicorn main:app --reload
