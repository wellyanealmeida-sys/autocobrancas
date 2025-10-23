// >>> CONFIG <<<
const API_BASE = window.location.hostname.includes('localhost') ? 'http://127.0.0.1:8000' : 'https://autocobrancas.onrender.com';
const PIX_INFO = 'chavepix@lwmutuomercantil.com.br';

const $ = s => document.querySelector(s);
const elList = $('#clientesList');

let editIndex = null;

function addAssocField(value=''){
  const div = document.createElement('div');
  div.className='assocItem';
  div.innerHTML = `<input placeholder="Nome do associado" value="${(value||'').replace(/"/g,'&quot;')}" />
                   <button class="ghost" type="button">Remover</button>`;
  div.querySelector('button').onclick = ()=> div.remove();
  $('#associadosList').appendChild(div);
}

$('#addAssoc').onclick = (e)=>{ e.preventDefault(); addAssocField(); };

$('#btnCancelEdit').onclick = ()=>{
  editIndex = null;
  $('#btnSubmit').textContent = 'Salvar';
  $('#btnCancelEdit').style.display='none';
};

$('#btnReload').onclick = ()=> carregarClientes();

$('#btnSubmit').onclick = async ()=>{
  const associados = Array.from(document.querySelectorAll('#associadosList input')).map(i=>i.value.trim()).filter(Boolean);
  const payload = {
    nome: $('#nome').value.trim(),
    valor_base: parseFloat($('#valor_base').value||0),
    data_credito: $('#data_credito').value,
    juros_diario: parseFloat($('#juros_diario').value||0),
    juros_mensal: parseFloat($('#juros_mensal').value||0),
    objeto_empenho: $('#objeto_empenho').value.trim(),
    documento: $('#documento').value.trim(),
    associados,
    telefone: $('#telefone').value.trim()
  };
  if(!payload.nome || !payload.data_credito){ alert('Preencha Nome e Data do Crédito.'); return; }

  if(editIndex===null){
    const r = await fetch(API_BASE + '/cadastrar', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok) return alert('Erro ao cadastrar');
  } else {
    const r = await fetch(API_BASE + '/editar/' + editIndex, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!r.ok) return alert('Erro ao atualizar');
    editIndex=null; $('#btnSubmit').textContent='Salvar'; $('#btnCancelEdit').style.display='none';
  }
  limparFormulario();
  carregarClientes();
};

function limparFormulario(){
  ['nome','valor_base','data_credito','juros_diario','juros_mensal','objeto_empenho','documento','telefone'].forEach(id=> $('#'+id).value='');
  $('#associadosList').innerHTML='';
  addAssocField();
}

async function carregarClientes(){
  try{
    const r = await fetch(API_BASE + '/clientes');
    const clientes = await r.json();
    elList.innerHTML='';
    clientes.forEach((c, idx)=>{
      const row = document.createElement('div');
      row.className='row';
      const jurosMes = (c.juros_mes != null ? c.juros_mes : (parseFloat(c.juros_diario||0)*30)).toFixed(2);
      row.innerHTML = `
        <div class="info">
          <div class="title">${c.nome||'-'}</div>
          <div class="meta">Valor atualizado: <b>R$ ${(Number(c.valor_total||0)).toFixed(2)}</b> • Dias: ${c.dias_corridos||0}</div>
          <div class="meta">Juros mensal: ${jurosMes}% • Juros diário: ${c.juros_diario||0}</div>
          <div class="meta">Telefone: ${c.telefone||'-'} • Data do crédito: ${c.data_credito||'-'}</div>
          <div class="meta">Associados: ${(c.associados||[]).join(', ') || '-'}</div>
        </div>
        <div class="btns">
          <button class="btn-whatsapp" type="button">💬 Enviar via WhatsApp</button>
          <button class="ghost" type="button">✏️ Editar</button>
          <button class="ghost" type="button">🗑️ Remover</button>
        </div>`;

      row.querySelector('.btn-whatsapp').onclick = ()=>{
        const msg =
`Olá ${c.nome}! 💰

Seu saldo atualizado de hoje é de R$ ${(Number(c.valor_total||0)).toFixed(2)}.
Data do crédito: ${c.data_credito||'-'}
Juros mensal: ${jurosMes}%
Juros diário: ${c.juros_diario||0}

Efetue o pagamento via PIX:
Chave: ${PIX_INFO}

Atenciosamente,
LW Mútuo Mercantil`;
        const phone = (c.telefone||'').replace(/\D/g,'');
        if(!phone){ alert('Telefone do cliente não cadastrado.'); return; }
        const url = 'https://wa.me/' + phone + '?text=' + encodeURIComponent(msg);
        window.open(url, '_blank');
      };

      row.querySelectorAll('.ghost')[0].onclick = ()=>{
        editIndex = idx;
        $('#btnSubmit').textContent = 'Salvar alteração';
        $('#btnCancelEdit').style.display='inline-block';
        $('#nome').value = c.nome||'';
        $('#valor_base').value = c.valor_base||'';
        $('#data_credito').value = c.data_credito||'';
        $('#juros_diario').value = c.juros_diario||'';
        $('#juros_mensal').value = c.juros_mensal||'';
        $('#objeto_empenho').value = c.objeto_empenho||'';
        $('#documento').value = c.documento||'';
        $('#telefone').value = c.telefone||'';
        const list = $('#associadosList'); list.innerHTML='';
        (c.associados||[]).forEach(a=> addAssocField(a));
        if((c.associados||[]).length===0) addAssocField();
        window.scrollTo({top:0,behavior:'smooth'});
      };

      row.querySelectorAll('.ghost')[1].onclick = async ()=>{
        if(!confirm('Remover cliente?')) return;
        const res = await fetch(API_BASE + '/cliente/' + idx, {method:'DELETE'});
        if(!res.ok) return alert('Erro ao remover');
        carregarClientes();
      };

      elList.appendChild(row);
    });
  }catch(err){
    console.error(err);
    elList.innerHTML = '<div class="meta">Erro ao carregar clientes. Verifique o backend.</div>';
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  addAssocField();
  carregarClientes();
});
