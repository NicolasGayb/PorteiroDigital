function atualizarUsuario(userId, campo, novoValor) {
    fetch(`/atualizar_usuario/${userId}`, {  // Certifique-se de que a rota está correta
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [campo]: novoValor })
    })
    .then(response => response.text())
    .then(data => console.log(data))
    .catch(error => console.error("Erro ao atualizar usuário:", error));
}