const API_BASE = window.location.hostname.includes('localhost') ? 'http://127.0.0.1:8000' : 'https://autocobrancas.onrender.com';
async function carregar(){
  const r = await fetch(API_BASE + '/clientes');
  const clientes = await r.json();
  const el = document.getElementById('clientes');
  el.innerHTML = '';
  clientes.forEach((c, idx) => {
    const div = document.createElement('div');
    div.className = 'client';
    div.innerHTML = `<div class="left"><strong>${c.nome}</strong><div>Valor atualizado: R$ ${Number(c.valor_total).toFixed(2)}</div><div>Dias: ${c.dias_corridos}</div><div>Associados: ${(c.associados||[]).join(', ')}</div></div>
      <div class="right">
        <button onclick="abrirWhats(${idx})">WhatsApp</button>
        <button onclick="editar(${idx})">Editar</button>
        <button onclick="deletar(${idx})">Remover</button>
      </div>`;
    el.appendChild(div);
  });
}

document.getElementById('addAssoc').addEventListener('click', (e)=>{ e.preventDefault(); addAssocInput(); });

function addAssocInput(value=''){
  const list = document.getElementById('associadosList');
  const wrapper = document.createElement('div'); wrapper.className='assoc';
  wrapper.innerHTML = `<input value="${value}" placeholder="Nome do associado"><button onclick="this.parentElement.remove()">Remover</button>`;
  list.appendChild(wrapper);
}

document.getElementById('btnSubmit').addEventListener('click', async ()=>{
  const associados = Array.from(document.querySelectorAll('#associadosList input')).map(i=>i.value).filter(Boolean);
  const payload = {
    nome: document.getElementById('nome').value,
    valor_base: document.getElementById('valor_base').value,
    data_credito: document.getElementById('data_credito').value,
    juros_diario: document.getElementById('juros_diario').value,
    juros_mensal: document.getElementById('juros_mensal').value,
    objeto_empenho: document.getElementById('objeto_empenho').value,
    documento: document.getElementById('documento').value,
    associados,
    telefone: document.getElementById('telefone').value
  };
  const r = await fetch(API_BASE + '/cadastrar', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(r.ok){ alert('Cadastrado'); carregar(); }
  else { alert('Erro ao cadastrar'); }
});

async function abrirWhats(idx){
  const r = await fetch(API_BASE + '/clientes');
  const clientes = await r.json();
  const c = clientes[idx];
  const phone = (c.telefone||'').replace(/\D/g,'');
  if(!phone){ alert('Telefone não cadastrado'); return; }
  const mensagem = `Olá ${c.nome}, sua cobrança atualizada é R$ ${Number(c.valor_total).toFixed(2)}.`;
  const send = await fetch(API_BASE + '/enviar_whatsapp/' + idx, {method:'POST'});
  const resp = await send.json();
  if(send.ok && resp.ok){
    alert('Mensagem enviada via API.');
  } else if(resp.wa_link) {
    window.open(resp.wa_link, '_blank');
  } else {
    alert('Erro ao enviar mensagem.');
  }
}

async function editar(idx){
  const r = await fetch(API_BASE + '/clientes');
  const clientes = await r.json();
  const c = clientes[idx];
  if(!c) return;
  document.getElementById('nome').value = c.nome || '';
  document.getElementById('valor_base').value = c.valor_base || '';
  document.getElementById('data_credito').value = c.data_credito || '';
  document.getElementById('juros_diario').value = c.juros_diario || '';
  document.getElementById('juros_mensal').value = c.juros_mensal || '';
  document.getElementById('objeto_empenho').value = c.objeto_empenho || '';
  document.getElementById('documento').value = c.documento || '';
  document.getElementById('telefone').value = c.telefone || '';
  document.getElementById('associadosList').innerHTML = '';
  (c.associados||[]).forEach(a=> addAssocInput(a));
  document.getElementById('btnSubmit').textContent = 'Salvar alteração';
  document.getElementById('btnSubmit').onclick = async ()=> {
    const associados = Array.from(document.querySelectorAll('#associadosList input')).map(i=>i.value).filter(Boolean);
    const payload = {
      nome: document.getElementById('nome').value,
      valor_base: document.getElementById('valor_base').value,
      data_credito: document.getElementById('data_credito').value,
      juros_diario: document.getElementById('juros_diario').value,
      juros_mensal: document.getElementById('juros_mensal').value,
      objeto_empenho: document.getElementById('objeto_empenho').value,
      documento: document.getElementById('documento').value,
      associados,
      telefone: document.getElementById('telefone').value
    };
    const res = await fetch(API_BASE + '/editar/' + idx, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(res.ok){ alert('Atualizado'); carregar(); document.getElementById('btnSubmit').textContent='Cadastrar / Atualizar'; location.reload(); }
    else alert('Erro ao atualizar');
  };
}

async function deletar(idx){
  if(!confirm('Remover cliente?')) return;
  const res = await fetch(API_BASE + '/cliente/' + idx, {method:'DELETE'});
  if(res.ok){ alert('Removido'); carregar(); } else alert('Erro ao remover');
}

carregar();
