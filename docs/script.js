const API_BASE = "https://autocobrancas.onrender.com";
const PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a";
const ADMIN_PASS = "lw2025";

let editIndex = null;
let cache = [];
let associadosArray = [];

// ---------- Utils ----------
function qs(id) { return document.getElementById(id); }
function fmtDataHora(iso) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleString("pt-BR"); } catch { return "-"; }
}

// ---------- Abas ----------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.getAttribute("data-tab");
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("show"));
    qs(tab).classList.add("show");
    if (tab === "tab-detalhes") {
      // conteúdo admin bloqueado
      if (qs("admin-content").style.display !== "block") {
        // aguarda senha
      } else {
        renderAdmin();
      }
    }
  });
});

function unlockAdmin() {
  const p = qs("admin-pass").value.trim();
  if (p === ADMIN_PASS) {
    qs("admin-lock").style.display = "none";
    qs("admin-content").style.display = "block";
    renderAdmin();
  } else {
    alert("Senha incorreta.");
  }
}

// ---------- Associados (chips) ----------
function refreshAssociadosChips() {
  const box = qs("associados-chips");
  box.innerHTML = associadosArray.map((n, idx) => `
    <span class="chip">${n} <button type="button" onclick="removeAssociado(${idx})">x</button></span>
  `).join("");
}
function addAssociado() {
  const val = qs("assoc-input").value.trim();
  if (!val) return;
  associadosArray.push(val);
  qs("assoc-input").value = "";
  refreshAssociadosChips();
}
function removeAssociado(i) {
  associadosArray.splice(i,1);
  refreshAssociadosChips();
}

// ---------- Carregar / Renderizar ----------
async function carregarClientes() {
  const res = await fetch(`${API_BASE}/clientes`);
  cache = await res.json();
  renderCobrancas();
  if (qs("admin-content").style.display === "block") renderAdmin();
}

function renderCobrancas() {
  const termo = (qs("busca")?.value || "").toLowerCase().trim();
  const ativos = cache.filter(c => (c.status || "ativo")==="ativo" && c.nome.toLowerCase().includes(termo));
  const quitados = cache.filter(c => (c.status || "ativo")==="quitado" && c.nome.toLowerCase().includes(termo));
  const inad = cache.filter(c => (c.status || "ativo")==="inadimplente" && c.nome.toLowerCase().includes(termo));
  renderLista(ativos, qs("lista-ativos"), "ativo");
  renderLista(quitados, qs("lista-quitados"), "quitado");
  renderLista(inad, qs("lista-inad"), "inad");
}

function cardHTML(c, idx, tipo) {
  const mensal = `${(c.juros_mensal ?? 0)}% → R$ ${(c.juros_mensal_valor ?? 0).toFixed(2)}`;
  const diario = `R$ ${(c.juros_diario_valor_dia ?? 0).toFixed(2)} × ${(c.dias_uteis_atraso ?? 0)} dias úteis (R$ ${(c.juros_diario_total ?? 0).toFixed(2)})`;
  const cls = tipo === "inad" ? "cliente-card inad" : "cliente-card";
  const vencRef = c.vencimento_atual || c.data_vencimento || "-";

  // Botões por tipo
  const btnsAtivo = `
    <button class="whatsapp" onclick="enviarWhatsapp(${idx})">💬 WhatsApp</button>
    <button class="edit" onclick="editarCliente(${idx})">✏️ Editar</button>
    <button class="edit" style="background:#8b5cf6" onclick="quitar(${idx})">💰 Quitar</button>
    <button class="edit" style="background:#0ea5e9" onclick="duplicar(${idx})">📋 Duplicar</button>
    <button class="edit" style="background:#6b7280" onclick="gerarRecibo(${idx})">📄 Recibo</button>
    <button class="delete" onclick="excluirCliente(${idx})">❌ Excluir</button>
  `;
  const btnsQuit = `
    <button class="edit" onclick="reativar(${idx})">♻️ Reativar</button>
    <button class="edit" style="background:#0ea5e9" onclick="duplicar(${idx})">📋 Duplicar</button>
    <button class="edit" style="background:#6b7280" onclick="gerarRecibo(${idx})">📄 Recibo</button>
    <button class="delete" onclick="excluirCliente(${idx})">❌ Excluir</button>
  `;
  const btnsInad = `
    <span class="note-inad">⚠️ Inadimplente há 3 meses — envio automático desativado.</span><br/>
    <button class="edit" onclick="editarCliente(${idx})">✏️ Editar</button>
    <button class="edit" style="background:#0ea5e9" onclick="duplicar(${idx})">📋 Duplicar</button>
    <button class="edit" style="background:#6b7280" onclick="gerarRecibo(${idx})">📄 Recibo</button>
    <button class="edit" onclick="reativar(${idx})">♻️ Mover p/ Ativos</button>
    <button class="delete" onclick="excluirCliente(${idx})">❌ Excluir</button>
  `;

  return `
    <div class="${cls}">
      <h3>${c.nome}${tipo==="inad" ? ' <span class="badge-inad">INADIMPLENTE</span>' : (tipo==="quitado" ? ' <span class="badge" style="background:#25d366;color:#fff;padding:2px 8px;border-radius:10px;font-size:12px;">QUITADO</span>' : '')}</h3>
      <p><b>Valor Crédito:</b> R$ ${(c.valor_credito ?? 0).toFixed(2)}</p>
      <p><b>Data de Vencimento:</b> ${vencRef}</p>
      <p><b>Juros Mensal:</b> ${mensal}</p>
      <p><b>Juros Diário:</b> ${diario}</p>
      <p><b>Valor Atualizado:</b> <b style="color:#d4af37">R$ ${(c.valor_total ?? 0).toFixed(2)}</b></p>
      <p style="color:#9aa; font-size:12px;"><b>Último envio:</b> ${fmtDataHora(c.ultimo_envio)}</p>
      <div class="buttons">
        ${tipo==="ativo" ? btnsAtivo : (tipo==="quitado" ? btnsQuit : btnsInad)}
      </div>
    </div>
  `;
}

function renderLista(arr, el, tipo) {
  el.innerHTML = arr.map(c => {
    const idx = cache.findIndex(k =>
      k.nome===c.nome && k.data_credito===c.data_credito && k.data_vencimento===c.data_vencimento
    );
    return cardHTML(c, idx, tipo);
  }).join("") || `<div class="cliente-card"><p>Nenhum cliente encontrado.</p></div>`;
}

// ---------- Admin Detalhes ----------
function renderAdmin() {
  const termo = (qs("busca-admin")?.value || "").toLowerCase().trim();
  const arr = cache.filter(c => c.nome.toLowerCase().includes(termo));
  qs("lista-admin").innerHTML = arr.map(c => `
    <div class="cliente-card">
      <h3>${c.nome} <span style="font-size:12px;color:#aaa;">(${c.status || "ativo"})</span></h3>
      <p><b>Telefone:</b> ${c.telefone || "-"}</p>
      <p><b>Valor Crédito:</b> R$ ${(c.valor_credito ?? 0).toFixed(2)}</p>
      <p><b>Data Crédito:</b> ${c.data_credito || "-"}</p>
      <p><b>Data Vencimento:</b> ${c.data_vencimento || "-"}</p>
      <p><b>Juros Mensal (%):</b> ${c.juros_mensal ?? 0}</p>
      <p><b>Juros Diário (R$/dia útil):</b> ${c.juros_diario_valor_dia?.toFixed(2) ?? (c.juros_diario_valor ?? 0).toFixed?.(2) ?? c.juros_diario_valor}</p>
      <p><b>Objeto de Empenho:</b> ${c.objeto_empenho || "-"}</p>
      <p><b>Documento / Procuração:</b> ${c.documento || "-"}</p>
      <p><b>Associados:</b> ${(Array.isArray(c.associados) ? c.associados.join(", ") : (c.associados || "")) || "-"}</p>
      <p><b>Último envio:</b> ${fmtDataHora(c.ultimo_envio)}</p>
      <p><b>Valor Atualizado (info):</b> R$ ${(c.valor_total ?? 0).toFixed(2)}</p>
    </div>
  `).join("") || `<div class="cliente-card"><p>Nenhum cliente encontrado.</p></div>`;
}

// Busca
["busca","busca-admin"].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener("input", () => {
    if (id==="busca") renderCobrancas(); else renderAdmin();
  });
});

// ---------- Salvar / Editar ----------
async function salvarCliente(ev) {
  ev.preventDefault();

  const payload = {
    nome: qs("nome").value.trim(),
    valor_credito: parseFloat(qs("valor_credito").value || 0),
    data_credito: qs("data_credito").value,
    data_vencimento: qs("data_vencimento").value,
    juros_mensal: parseFloat(qs("juros_mensal").value || 0),
    juros_diario_valor: parseFloat(qs("juros_diario").value || 0),
    objeto_empenho: qs("objeto_empenho").value.trim(),
    documento: qs("documento").value.trim(),
    associados: associadosArray.slice(), // envia lista
    telefone: qs("telefone").value.trim(),
  };

  if (editIndex !== null) {
    const res = await fetch(`${API_BASE}/clientes`);
    const atual = await res.json();
    payload.status = atual[editIndex]?.status || "ativo";
    payload.ultimo_envio = atual[editIndex]?.ultimo_envio || null;
  }

  const url = editIndex !== null ? `${API_BASE}/editar/${editIndex}` : `${API_BASE}/cadastrar`;
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!r.ok) { alert("Erro ao salvar: " + (await r.text())); return; }

  alert(editIndex !== null ? "Cliente atualizado!" : "Cliente cadastrado!");
  document.getElementById("cliente-form").reset();
  associadosArray = []; refreshAssociadosChips();
  editIndex = null;
  await carregarClientes();
}

async function editarCliente(i) {
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const c = clientes[i];
  editIndex = i;

  qs("nome").value = c.nome || "";
  qs("valor_credito").value = c.valor_credito || "";
  qs("data_credito").value = c.data_credito || "";
  qs("data_vencimento").value = c.data_vencimento || "";
  qs("juros_mensal").value = c.juros_mensal || "";
  qs("juros_diario").value = c.juros_diario_valor_dia || c.juros_diario_valor || "";
  qs("objeto_empenho").value = c.objeto_empenho || "";
  qs("documento").value = c.documento || "";
  qs("telefone").value = c.telefone || "";

  associadosArray = Array.isArray(c.associados)
    ? c.associados.slice()
    : (typeof c.associados === "string" && c.associados ? c.associados.split(",").map(s=>s.trim()) : []);
  refreshAssociadosChips();

  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function excluirCliente(i) {
  if (!confirm("Excluir este cliente?")) return;
  await fetch(`${API_BASE}/cliente/${i}`, { method: "DELETE" });
  carregarClientes();
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

// ---------- WhatsApp (sem associados na mensagem) ----------
async function enviarWhatsapp(i) {
  await fetch(`${API_BASE}/registrar_envio/${i}`, { method: "POST" });
  await carregarClientes();
  const c = cache[i];
  if (!c || !c.telefone) return alert("Telefone não cadastrado!");

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

  window.open(`https://wa.me/${c.telefone}?text=${encodeURIComponent(mensagem)}`, "_blank");
}

// ---------- Exportar ----------
function exportarJSON() {
  const blob = new Blob([JSON.stringify(cache, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "clientes.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

function exportarCSV() {
  if (!cache.length) { alert("Sem dados para exportar."); return; }
  // Cabeçalhos com TODOS os campos
  const headers = [
    "nome","telefone","valor_credito","data_credito","data_vencimento",
    "juros_mensal","juros_mensal_valor","juros_diario_valor_dia","dias_uteis_atraso",
    "juros_diario_total","valor_total","objeto_empenho","documento","associados","status","ultimo_envio"
  ];
  const rows = cache.map(c => [
    c.nome || "", c.telefone || "", c.valor_credito || 0, c.data_credito || "", c.data_vencimento || "",
    c.juros_mensal || 0, c.juros_mensal_valor || 0, c.juros_diario_valor_dia || c.juros_diario_valor || 0, c.dias_uteis_atraso || 0,
    c.juros_diario_total || 0, c.valor_total || 0, c.objeto_empenho || "", c.documento || "",
    Array.isArray(c.associados) ? c.associados.join("; ") : (c.associados || ""),
    c.status || "ativo", c.ultimo_envio || ""
  ]);

  const csv = [headers.join(","), ...rows.map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "clientes.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

async function duplicar(i) {
  if (!confirm("Duplicar este cadastro como nova operação?")) return;
  const res = await fetch(`${API_BASE}/clientes`);
  const clientes = await res.json();
  const c = clientes[i];

  const payload = {
    ...c,
    data_credito: new Date().toISOString().slice(0,10),
    status: "ativo",
    ultimo_envio: null
  };
  // limpa campos que o backend recalcula
  delete payload.valor_total;
  delete payload.juros_mensal_valor;
  delete payload.juros_diario_valor_dia;
  delete payload.juros_diario_total;
  delete payload.dias_uteis_atraso;
  delete payload.vencimentos;
  delete payload.vencimento_atual;

  await fetch(`${API_BASE}/cadastrar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  alert("Cadastro duplicado como nova operação.");
  carregarClientes();
}

function gerarRecibo(i) {
  alert("Recibo PDF será gerado (jsPDF) na próxima etapa — envio manual.");
}

// ---------- Eventos ----------
document.getElementById("cliente-form").addEventListener("submit", salvarCliente);
document.getElementById("busca").addEventListener("input", renderCobrancas);
const ba = document.getElementById("busca-admin"); if (ba) ba.addEventListener("input", renderAdmin);
carregarClientes();
