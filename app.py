from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

# URL do banco de dados (pode ser ajustada para produção)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///usuarios.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Administrador, Dono do prédio, Zelador, Condomino

# Rota inicial - login e cadastro
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo

            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('painel'))
        else:
            flash("Credenciais inválidas", "danger")

    return render_template('login.html')

# Rota de cadastro
@app.route('/register', methods=['POST'])
def register():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    confirma = request.form['confirma_senha']

    if senha != confirma:
        flash("As senhas não coincidem.", "danger")
        return redirect(url_for('login'))

    usuario_existente = Usuario.query.filter_by(email=email).first()
    if usuario_existente:
        flash("Já existe um usuário com esse email.", "warning")
        return redirect(url_for('login'))

    hash_senha = generate_password_hash(senha)
    novo_usuario = Usuario(nome=nome, email=email, senha=hash_senha, tipo='Condomino')  # padrão
    db.session.add(novo_usuario)
    db.session.commit()

    flash("Usuário cadastrado com sucesso!", "success")
    return redirect(url_for('login'))

# Rota do painel (redireciona conforme tipo de usuário)
@app.route('/painel')
def painel():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    tipo = session['tipo']
    if tipo == 'Zelador':
        return redirect(url_for('painel_zelador'))
    elif tipo == 'Condomino':
        return redirect(url_for('painel_condomino'))
    elif tipo == 'Administrador':
        return redirect(url_for('painel_admin'))
    elif tipo == 'Proprietario':
        return redirect(url_for('painel_dono'))
    else:
        return "Tipo de usuário não reconhecido"

# Painel do zelador
@app.route('/painel/zelador')
def painel_zelador():
    return "Painel do Zelador - Aqui ele pode registrar entregas."

# Painel do condômino
@app.route('/painel/condomino')
def painel_condomino():
    return "Painel do Condômino - Aqui ele pode visualizar entregas."

# Painel do dono do condomínio
@app.route('/painel/dono')
def painel_dono():
    return "Painel do Dono do Prédio - Aqui ele pode gerenciar o condomínio."

# Painel do administrador
@app.route('/painel/admin')
def painel_admin():
    return "Painel do Administrador - Aqui ele pode gerenciar usuários e configurações."
# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Você saiu da sessão.", "info")
    return redirect(url_for('login'))

# Inicialização
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
