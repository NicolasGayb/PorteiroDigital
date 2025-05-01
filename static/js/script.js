// Função para ativar os campos editáveis ao clicar em "Editar"
function editarUsuario(userId) {
    document.getElementById(`nome-${userId}`).disabled = false;  // Habilita edição do nome
    document.getElementById(`email-${userId}`).disabled = false;  // Habilita edição do email
    document.getElementById(`tipo-${userId}`).disabled = false;  // Habilita edição do tipo

    document.getElementById(`salvar-${userId}`).classList.remove("d-none"); // Mostra botão "Salvar"
}

// Função para enviar as alterações ao servidor
function salvarUsuario(userId) {
    // Obtém os valores atualizados dos campos
    const nome = document.getElementById(`nome-${userId}`).value;
    const email = document.getElementById(`email-${userId}`).value;
    const tipo = document.getElementById(`tipo-${userId}`).value;

    // Envia requisição para atualizar o usuário
    fetch(`/atualizar_usuario/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, email, tipo })  // Transforma os dados em JSON
    })
    .then(response => response.text())  // Obtém resposta do backend
    .then(data => {
        alert("Usuário atualizado com sucesso!");  // Mostra alerta de sucesso

        // Desabilita novamente os campos após salvar
        document.getElementById(`nome-${userId}`).disabled = true;
        document.getElementById(`email-${userId}`).disabled = true;
        document.getElementById(`tipo-${userId}`).disabled = true;

        document.getElementById(`salvar-${userId}`).classList.add("d-none"); // Esconde botão "Salvar"
    })
    .catch(error => console.error("Erro ao atualizar usuário:", error));  // Captura erros
}