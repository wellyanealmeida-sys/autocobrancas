const form = document.getElementById('formCliente');
const tabela = document.getElementById('tabelaClientes').querySelector('tbody');
const apiUrl = '/cobrancas'; // ajuste para o endpoint do backend

async function carregarClientes() {
    try {
        const resp = await fetch(apiUrl);
        const clientes = await resp.json();
        tabela.innerHTML = '';
        clientes.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${c.nome}</td>
                <td>${c.valor_base.toFixed(2)}</td>
                <td>${c.juros_diario.toFixed(2)}</td>
                <td>${c.dias}</td>
                <td>${c.valor_atualizado.toFixed(2)}</td>
                <td><a href="https://wa.me/${c.telefone}?text=Olá ${c.nome}, sua cobrança atualizada é R$${c.valor_atualizado.toFixed(2)}" target="_blank">💬 WhatsApp</a></td>
            `;
            tabela.appendChild(tr);
        });
    } catch(err) {
        console.error('Erro ao carregar clientes:', err);
    }
}

form.addEventListener('submit', async e => {
    e.preventDefault();
    const dados = {
        nome: document.getElementById('nome').value,
        valor_base: parseFloat(document.getElementById('valor_base').value),
        data_emprestimo: document.getElementById('data_emprestimo').value,
        juros_diario: parseFloat(document.getElementById('juros_diario').value),
        objeto_empenho: document.getElementById('objeto_empenho').value,
        documento: document.getElementById('documento').value,
        associado: document.getElementById('associado').value
    };
    try {
        const resp = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if(resp.ok) {
            form.reset();
            carregarClientes();
        } else {
            alert('Erro ao enviar dados');
        }
    } catch(err) {
        console.error('Erro no envio:', err);
    }
});

carregarClientes();