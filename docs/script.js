const API_BASE = "https://autocobrancas.onrender.com";
const PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a";

async function carregarClientes() {
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const list = document.getElementById("clientes-list");
  list.innerHTML = "";

  clientes.forEach((c, i) => {
    const card = document.createElement("div");
    card.className = "cliente-card";
    card.innerHTML = `
      <h3>${c.nome}</h3>
      <p><b>Valor Crédito:</b> R$ ${c.valor_credito?.toFixed(2)}</p>
      <p><b>Data Crédito:</b> ${c.data_credito}</p>
      <p><b>Data Vencimento:</b> ${c.data_vencimento}</p>
      <p><b>Juros Mensal:</b> ${c.juros_mensal}% → R$ ${c.juros_mensal_valor?.toFixed(2)}</p>
      <p><b>Juros Diário:</b> ${c.juros_diario}% (${c.dias_uteis_atraso} dias úteis) → R$ ${c.juros_diario_valor?.toFixed(2)}</p>
      <p><b>Valor Atualizado:</b> <b style="color:#d4af37">R$ ${c.valor_total?.toFixed(2)}</b></p>
      <div class="buttons">
        <button class="whatsapp" onclick="enviarWhatsapp(${i})">💬 WhatsApp</button>
        <button class="edit" onclick="editarCliente(${i})">✏️ Editar</button>
        <button class="delete" onclick="excluirCliente(${i})">❌ Excluir</button>
      </div>
    `;
    list.appendChild(card);
  });
}

async function salvarCliente(ev) {
  ev.preventDefault();
  const payload = {
    nome: nome.value.trim(),
    valor_credito: parseFloat(valor_credito.value || 0),
    data_credito: data_credito.value,
    data_vencimento: data_vencimento.value,
    juros_mensal: parseFloat(juros_mensal.value || 0),
    juros_diario: parseFloat(juros_diario.value || 0),
    objeto_empenho: objeto_empenho.value.trim(),
    documento: documento.value.trim(),
    associados: associados.value.trim(),
    telefone: telefone.value.trim()
  };

  await fetch(`${API_BASE}/cadastrar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  alert("Cliente salvo com sucesso!");
  document.getElementById("cliente-form").reset();
  carregarClientes();
}

async function excluirCliente(i) {
  if (!confirm("Excluir este cliente?")) return;
  await fetch(`${API_BASE}/cliente/${i}`, { method: "DELETE" });
  carregarClientes();
}

function editarCliente(i) {
  alert("Abra o painel de edição — funcionalidade simples pode ser adicionada depois.");
}

async function enviarWhatsapp(i) {
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const c = clientes[i];
  if (!c.telefone) return alert("Telefone não cadastrado!");

  const mensagem = `Olá ${c.nome}! 💰

Seu saldo atualizado de hoje é de R$ ${c.valor_total.toFixed(2)}.
Data do crédito: ${c.data_credito}
Data de vencimento: ${c.data_vencimento}
Juros mensal: ${c.juros_mensal}% 
Juros diário: ${c.juros_diario}% (após vencimento)

Efetue o pagamento via PIX:
Chave: ${PIX_KEY}

Atenciosamente,
LW Mútuo Mercantil`;

  const url = `https://wa.me/${c.telefone}?text=${encodeURIComponent(mensagem)}`;
  window.open(url, "_blank");
}

document.getElementById("cliente-form").addEventListener("submit", salvarCliente);
carregarClientes();
