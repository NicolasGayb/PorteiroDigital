// Função para ativar os campos editáveis ao clicar em "Editar"
function editarUsuario(userId) {
    document.getElementById(`nome-${userId}`).disabled = false;  // Habilita edição do nome
    document.getElementById(`email-${userId}`).disabled = false;  // Habilita edição do email
    document.getElementById(`tipo-${userId}`).disabled = false;  // Habilita edição do tipo

    document.getElementById(`salvar-${userId}`).classList.remove("d-none"); // Mostra botão "Salvar"
    document.getElementById(`cancelar-${userId}`).classList.remove("d-none"); // Mostra botão "Cancelar"
    document.getElementById(`editar-${userId}`).classList.add("d-none"); // Esconde botão "Editar"
    document.getElementById(`deletar-${userId}`).classList.add("d-none"); // Esconde botão "Deletar"

    // Salva os valores originais para restaurá-los caso o usuário cancele
    document.getElementById(`nome-${userId}`).dataset.original = document.getElementById(`nome-${userId}`).value;
    document.getElementById(`email-${userId}`).dataset.original = document.getElementById(`email-${userId}`).value;
    document.getElementById(`tipo-${userId}`).dataset.original = document.getElementById(`tipo-${userId}`).value;
}

// Função para cancelar a edição e restaurar valores originais
function cancelarEdicao(userId) {
    document.getElementById(`nome-${userId}`).value = document.getElementById(`nome-${userId}`).dataset.original;
    document.getElementById(`email-${userId}`).value = document.getElementById(`email-${userId}`).dataset.original;
    document.getElementById(`tipo-${userId}`).value = document.getElementById(`tipo-${userId}`).dataset.original;

    document.getElementById(`nome-${userId}`).disabled = true;
    document.getElementById(`email-${userId}`).disabled = true;
    document.getElementById(`tipo-${userId}`).disabled = true;

    document.getElementById(`salvar-${userId}`).classList.add("d-none");  // Esconde botão Salvar
    document.getElementById(`cancelar-${userId}`).classList.add("d-none");  // Esconde botão Cancelar
    document.getElementById(`editar-${userId}`).classList.remove("d-none");  // Mostra botão Editar
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
        document.getElementById(`cancelar-${userId}`).classList.add("d-none"); // Esconde botão "Cancelar"
        document.getElementById(`editar-${userId}`).classList.remove("d-none"); // Mostra botão "Editar"
        document.getElementById(`deletar-${userId}`).classList.remove("d-none"); // Mostra botão "Deletar"
    })
    .catch(error => console.error("Erro ao atualizar usuário:", error));  // Captura erros
}