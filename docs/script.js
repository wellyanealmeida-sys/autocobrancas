const API_BASE = "https://autocobrancas.onrender.com";

async function salvarCliente() {
  const data = {
    nome: document.getElementById("nome").value,
    telefone: document.getElementById("telefone").value,
    tipo_telefone: document.getElementById("tipoTelefone").value,
    valor: parseFloat(document.getElementById("valor").value),
    data_credito: document.getElementById("dataCredito").value,
    primeiro_vencimento: document.getElementById("primeiroVencimento").value,
    dias: parseInt(document.getElementById("dias").value),
    juros: parseFloat(document.getElementById("juros").value),
    associados: document.getElementById("associados").value
  };

  const resp = await fetch(`${API_BASE}/cadastrar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });

  if (!resp.ok) {
    alert("Erro ao salvar");
    return;
  }

  alert("Cadastro salvo com sucesso!");
}
