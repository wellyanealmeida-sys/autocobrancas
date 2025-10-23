const API_BASE = "https://autocobrancas.onrender.com";
const PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a";

let editIndex = null;

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
      <p><b>Juros Diário:</b> R$ ${c.juros_diario_valor_dia?.toFixed(2)} × ${c.dias_uteis_atraso} dias úteis → R$ ${c.juros_diario_total?.toFixed(2)}</p>
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
    juros_diario_valor: parseFloat(juros_diario.value || 0), // em R$ por dia útil
    objeto_empenho: objeto_empenho.value.trim(),
    documento: documento.value.trim(),
    associados: associados.value.trim(),
    telefone: telefone.value.trim()
  };

  const url = editIndex !== null
    ? `${API_BASE}/editar/${editIndex}`
    : `${API_BASE}/cadastrar`;

  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  alert(editIndex !== null ? "Cliente atualizado!" : "Cliente cadastrado!");
  document.getElementById("cliente-form").reset();
  editIndex = null;
  carregarClientes();
}

async function excluirCliente(i) {
  if (!confirm("Excluir este cliente?")) return;
  await fetch(`${API_BASE}/cliente/${i}`, { method: "DELETE" });
  carregarClientes();
}

async function editarCliente(i) {
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const c = clientes[i];
  editIndex = i;

  nome.value = c.nome;
  valor_credito.value = c.valor_credito;
  data_credito.value = c.data_credito;
  data_vencimento.value = c.data_vencimento;
  juros_mensal.value = c.juros_mensal;
  juros_diario.value = c.juros_diario_valor_dia;
  objeto_empenho.value = c.objeto_empenho || "";
  documento.value = c.documento || "";
  associados.value = c.associados || "";
  telefone.value = c.telefone || "";

  window.scrollTo({ top: 0, behavior: "smooth" });
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
Juros mensal: ${c.juros_mensal}% (R$ ${c.juros_mensal_valor.toFixed(2)})
Juros diário: R$ ${c.juros_diario_valor_dia.toFixed(2)} × ${c.dias_uteis_atraso} dias úteis (R$ ${c.juros_diario_total.toFixed(2)})

Efetue o pagamento via PIX:
Chave: ${PIX_KEY}

Atenciosamente,
LW Mútuo Mercantil`;

  const url = `https://wa.me/${c.telefone}?text=${encodeURIComponent(mensagem)}`;
  window.open(url, "_blank");
}

document.getElementById("cliente-form").addEventListener("submit", salvarCliente);
carregarClientes();
