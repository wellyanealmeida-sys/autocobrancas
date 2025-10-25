const API_BASE = "https://autocobrancas.onrender.com";
const PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a";

let editIndex = null;
let cache = []; // cache da última lista vinda do backend

// ======== CARREGAR CLIENTES ========
async function carregarClientes() {
  const res = await fetch(`${API_BASE}/clientes`);
  cache = await res.json();
  renderizar();
}

// ======== RENDERIZAÇÃO (busca e separação de listas) ========
function renderizar() {
  const termo = (document.getElementById("busca").value || "").toLowerCase().trim();
  const ativos = cache.filter(
    (c) => (c.status || "ativo") === "ativo" && c.nome.toLowerCase().includes(termo)
  );
  const quitados = cache.filter(
    (c) => (c.status || "ativo") === "quitado" && c.nome.toLowerCase().includes(termo)
  );
  renderLista(ativos, document.getElementById("lista-ativos"), true);
  renderLista(quitados, document.getElementById("lista-quitados"), false);
}

function cardHTML(c, i, isAtivo) {
  const jurosMensal = `${(c.juros_mensal ?? 0)}% → R$ ${(c.juros_mensal_valor ?? 0).toFixed(2)}`;
  const diarioLinha = `R$ ${(c.juros_diario_valor_dia ?? 0).toFixed(2)} × ${
    c.dias_uteis_atraso ?? 0
  } dias úteis → R$ ${(c.juros_diario_total ?? 0).toFixed(2)}`;
  return `
    <div class="cliente-card">
      <h3>${c.nome} ${!isAtivo ? ' <span style="color:#25d366;font-size:12px;">(quitado)</span>' : ''}</h3>
      <p><b>Valor Crédito:</b> R$ ${(c.valor_credito ?? 0).toFixed(2)}</p>
      <p><b>Data Vencimento:</b> ${c.data_vencimento}</p>
      <p><b>Juros Mensal:</b> ${jurosMensal}</p>
      <p><b>Juros Diário:</b> ${diarioLinha}</p>
      <p><b>Valor Atualizado:</b> <b style="color:#d4af37">R$ ${(c.valor_total ?? 0).toFixed(2)}</b></p>
      <div class="buttons">
        ${isAtivo ? `<button class="whatsapp" onclick="enviarWhatsapp(${i})">💬 WhatsApp</button>` : ""}
        ${isAtivo ? `<button class="edit" onclick="editarCliente(${i})">✏️ Editar</button>` : ""}
        ${isAtivo ? `<button class="delete" onclick="excluirCliente(${i})">❌ Excluir</button>` : `<button class="delete" onclick="excluirCliente(${i})">❌ Excluir</button>`}
        ${isAtivo ? `<button class="edit" style="background:#8b5cf6" onclick="quitar(${i})">💰 Quitar</button>` : `<button class="edit" style="background:#0ea5e9" onclick="reativar(${i})">♻️ Reativar</button>`}
      </div>
    </div>
  `;
}

function renderLista(arr, el, isAtivo) {
  el.innerHTML =
    arr
      .map((c) => {
        const idxReal = cache.findIndex(
          (k) =>
            k.nome === c.nome &&
            k.data_credito === c.data_credito &&
            k.data_vencimento === c.data_vencimento
        );
        return cardHTML(c, idxReal, isAtivo);
      })
      .join("") || `<div class="cliente-card"><p>Nenhum cliente encontrado.</p></div>`;
}

// ======== SALVAR CLIENTE ========
async function salvarCliente(ev) {
  ev.preventDefault();

  const payload = {
    nome: nome.value.trim(),
    valor_credito: parseFloat(valor_credito.value || 0),
    data_credito: data_credito.value,
    data_vencimento: data_vencimento.value,
    juros_mensal: parseFloat(juros_mensal.value || 0),
    juros_diario_valor: parseFloat(juros_diario.value || 0),
    objeto_empenho: objeto_empenho.value.trim(),
    documento: documento.value.trim(),
    associados: associados.value.trim(),
    telefone: telefone.value.trim(),
  };

  // manter status anterior ao editar
  if (editIndex !== null) {
    const res = await fetch(`${API_BASE}/clientes`);
    const atual = await res.json();
    payload.status = atual[editIndex]?.status || "ativo";
  }

  const url = editIndex !== null ? `${API_BASE}/editar/${editIndex}` : `${API_BASE}/cadastrar`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!r.ok) {
    const t = await r.text();
    alert("Erro ao salvar: " + t);
    return;
  }

  alert(editIndex !== null ? "Cliente atualizado!" : "Cliente cadastrado!");
  document.getElementById("cliente-form").reset();
  editIndex = null;
  await carregarClientes();
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

// ======== EDIÇÃO, EXCLUSÃO, QUITAÇÃO ========
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

  nome.value = c.nome || "";
  valor_credito.value = c.valor_credito || "";
  data_credito.value = c.data_credito || "";
  data_vencimento.value = c.data_vencimento || "";
  juros_mensal.value = c.juros_mensal || "";
  juros_diario.value = c.juros_diario_valor_dia || "";
  objeto_empenho.value = c.objeto_empenho || "";
  documento.value = c.documento || "";
  associados.value = c.associados || "";
  telefone.value = c.telefone || "";

  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function quitar(i) {
  if (!confirm("Marcar este cliente como quitado?")) return;
  await fetch(`${API_BASE}/quitar/${i}`, { method: "POST" });
  carregarClientes();
}

async function reativar(i) {
  if (!confirm("Reativar este cliente?")) return;
  await fetch(`${API_BASE}/reativar/${i}`, { method: "POST" });
  carregarClientes();
}

// ======== ENVIO DE WHATSAPP (mensagem atualizada) ========
async function enviarWhatsapp(i) {
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const c = clientes[i];
  if (!c.telefone) return alert("Telefone não cadastrado!");

  // saldo = juros mensal + juros diário
  const saldo_total = (c.juros_mensal_valor || 0) + (c.juros_diario_total || 0);

  const mensagem = `Olá ${c.nome}! 💰

Seu saldo atualizado de hoje é de R$ ${saldo_total.toFixed(2)}.
Data de vencimento: ${c.data_vencimento}
Juros mensal: R$ ${c.juros_mensal_valor.toFixed(2)}
Juros diário: R$ ${c.juros_diario_total.toFixed(2)} (R$ ${c.juros_diario_valor_dia.toFixed(2)} por dia útil)

Efetue o pagamento via PIX:
Chave: ${PIX_KEY}

Atenciosamente,
LW Mútuo Mercantil`;

  const url = `https://wa.me/${c.telefone}?text=${encodeURIComponent(mensagem)}`;
  window.open(url, "_blank");
}

// ======== EVENTOS ========
document.getElementById("cliente-form").addEventListener("submit", salvarCliente);
document.getElementById("busca").addEventListener("input", renderizar);
carregarClientes();
