<script>
const API_BASE = "https://autocobrancas.onrender.com";
const PIX_KEY = "dcb448d4-2b4b-4f25-9097-95d800d3638a";
const CNPJ_PIX = "59014280000130";

let CLIENTES_CACHE = [];

// Formata dinheiro em R$
function money(n){
  return (Number(n||0)).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
}

// Converte "YYYY-MM-DD" para "DD/MM/YYYY"
function formatDateBr(iso){
  if(!iso) return "-";
  const [y,m,d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

// Hoje em formato YYYY-MM-DD
function hojeISO(){
  return new Date().toISOString().slice(0,10);
}

// Pega o ciclo atual (do vencimento_atual) ou o último
function cicloAtual(cli){
  const ciclos = cli.ciclos || [];
  if(!ciclos.length) return null;
  const atual = ciclos.find(ci => ci.vencimento === cli.vencimento_atual);
  return atual || ciclos[ciclos.length-1];
}

// Carrega clientes da API e atualiza tela
async function load(){
  const r = await fetch(API_BASE + '/clientes');
  const arr = await r.json();
  CLIENTES_CACHE = arr;
  document.getElementById('lista').innerHTML =
    arr.map((c,i)=>card(c,i)).join('') || '<p>Nenhum cliente.</p>';
  renderAssociados();
}

// Monta o card de cada cliente
function card(c,i){
  const atual = cicloAtual(c);
  const podeEnviarHoje = c.vencimento_atual === hojeISO() && (c.status || 'ativo') === 'ativo';

  const linhas = (c.ciclos || []).map(ci => `
    <li>
      • Vencimento: ${formatDateBr(ci.vencimento)}<br>
      &nbsp;&nbsp; Juros do mês: ${money(ci.juros_mensal_valor)}<br>
      &nbsp;&nbsp; Juros diário total (${ci.dias_uteis} dias úteis): ${money(ci.juros_diario_total)}<br>
      &nbsp;&nbsp; Valor atualizado: <b>${money(ci.valor_atualizado)}</b>
    </li>
  `).join('');

  return `
    <div class='cli'>
      <h3>${c.nome} <small>(${c.status})</small></h3>
      <p><b>Telefone:</b> ${c.telefone}</p>
      <p><b>Valor Crédito:</b> ${money(c.valor_credito)}</p>
      <p><b>Vencimento atual:</b> ${formatDateBr(c.vencimento_atual || c.data_vencimento)}</p>
      ${c.objeto ? `<p><b>Objeto em garantia:</b> ${c.objeto}</p>` : ""}
      ${c.associados && c.associados.length ? `<p><b>Associados:</b> ${c.associados.join(", ")}</p>` : ""}
      ${atual ? `<p><b>Valor para pagamento (hoje):</b> ${money(atual.valor_atualizado)}</p>` : ""}
      <details><summary>Detalhes dos ciclos</summary><ul>${linhas}</ul></details>
      <div class='acoes'>
        <button class='btn' onclick='editar(${i})'>✏️ Editar</button>
        <button class='btn' onclick='zap(${i})' ${podeEnviarHoje ? "" : "disabled title='Só libera no dia do vencimento atual'"}>💬 WhatsApp</button>
      </div>
    </div>
  `;
}

// Monta mensagem de WhatsApp (sem valor de crédito, com CNPJ)
async function zap(i){
  const c = CLIENTES_CACHE[i];
  if(!c) return;

  const atual = cicloAtual(c);
  const valorHoje = atual ? atual.valor_atualizado : c.valor_credito;
  const dataVenc = formatDateBr(c.vencimento_atual || (atual && atual.vencimento) || c.data_vencimento);

  let msg = `Olá ${c.nome}, tudo bem?\\n\\n`;
  msg += `Aqui é da LW Mútuo Mercantil.\\n\\n`;
  msg += `Estamos lembrando que hoje, dia ${dataVenc}, vence o pagamento referente ao seu contrato.`;
  if (c.objeto) {
    msg += ` Objeto em garantia: ${c.objeto}.`;
  }
  msg += `\\n\\n`;
  msg += `Valor para pagamento hoje (com juros do mês e juros diário conforme combinado): ${money(valorHoje)}.\\n\\n`;
  msg += `Chaves PIX para pagamento:\\n`;
  msg += `• Chave padrão: ${PIX_KEY}\\n`;
  msg += `• CNPJ: ${CNPJ_PIX}\\n\\n`;
  msg += `Após o pagamento, por favor envie o comprovante neste número para atualização do sistema.\\n\\n`;
  msg += `Qualquer dúvida, estamos à disposição.`;

  const url = `https://wa.me/${c.telefone}?text=${encodeURIComponent(msg)}`;
  window.open(url, '_blank');
}

// Preenche formulário para edição
function editar(i){
  const c = CLIENTES_CACHE[i];
  if(!c) return;
  const f = document.getElementById('form');
  f.dataset.index = i;
  f.nome.value = c.nome || "";
  f.telefone.value = c.telefone || "";
  f.valor_credito.value = c.valor_credito || "";
  f.data_credito.value = (c.data_credito || "").slice(0,10);
  f.data_vencimento.value = (c.data_vencimento || c.vencimento_atual || "").slice(0,10);
  f.juros_mensal.value = c.juros_mensal || "";
  f.juros_diario.value = c.juros_diario_valor || c.juros_diario || "";
  f.objeto.value = c.objeto || "";
  f.associados.value = (c.associados || []).join(", ");
  f.nome.focus();
}

// --------- GUIA DE ASSOCIADOS ---------

function coletarAssociadosLista(){
  const linhas = [];
  CLIENTES_CACHE.forEach(c => {
    (c.associados || []).forEach(a => {
      linhas.push({
        associado: a,
        cliente: c.nome,
        telefone: c.telefone,
        status: c.status || 'ativo',
        vencimento_atual: formatDateBr(c.vencimento_atual || c.data_vencimento)
      });
    });
  });
  return linhas;
}

function renderAssociados(){
  const cont = document.getElementById('associados');
  if(!cont) return;
  const linhas = coletarAssociadosLista();
  if(!linhas.length){
    cont.innerHTML = "<p>Nenhum associado cadastrado.</p>";
    return;
  }
  const rowsHtml = linhas.map(l => `
    <tr>
      <td>${l.associado}</td>
      <td>${l.cliente}</td>
      <td>${l.telefone}</td>
      <td>${l.status}</td>
      <td>${l.vencimento_atual}</td>
    </tr>
  `).join('');
  cont.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Associado</th><th>Cliente</th><th>Telefone</th><th>Status</th><th>Vencimento atual</th>
        </tr>
      </thead>
      <tbody>${rowsHtml}</tbody>
    </table>
  `;
}

function exportarAssociadosCSV(){
  const linhas = coletarAssociadosLista();
  if(!linhas.length){
    alert("Nenhum associado para exportar.");
    return;
  }
  const header = ["Associado","Cliente","Telefone","Status","Vencimento atual"];
  const csvRows = [header.join(";")].concat(
    linhas.map(l => [l.associado,l.cliente,l.telefone,l.status,l.vencimento_atual].join(";"))
  );
  const blob = new Blob([csvRows.join("\\n")], {type:"text/csv;charset=utf-8;"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "associados.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// --------- SUBMIT DO FORM ---------

document.getElementById('form').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const f = e.target;
  const associados = f.associados.value
    .split(',')
    .map(s => s.trim())
    .filter(s => s.length);

  const payload = {
    nome: f.nome.value.trim(),
    telefone: f.telefone.value.trim(),
    valor_credito: f.valor_credito.value,
    data_credito: f.data_credito.value || null,
    data_vencimento: f.data_vencimento.value || null,
    juros_mensal: f.juros_mensal.value,
    juros_diario_valor: f.juros_diario.value,
    objeto: f.objeto.value.trim() || null,
    associados: associados
  };

  const idx = f.dataset.index;
  let url = API_BASE + '/cadastrar';
  if(idx !== undefined && idx !== ""){
    url = API_BASE + '/editar/' + idx;
  }

  const r = await fetch(url,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(!r.ok){
    const txt = await r.text();
    alert('Erro ao salvar: ' + txt);
    return;
  }
  f.reset();
  delete f.dataset.index;
  load();
});

// Inicializa a tela
load();
</script>
