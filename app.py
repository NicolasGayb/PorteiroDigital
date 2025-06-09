from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///usuarios.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Tipos: Administrador, Dono do prédio, Zelador, Condomino
    destinatario = db.Column(db.String(100), nullable=False)  # Destinatário será sempre igual ao nome completo

    # Garante que destinatario sempre seja igual ao nome ao criar ou editar um usuário
    def __init__(self, nome, email, senha, tipo):
        self.nome = nome
        self.email = email
        self.senha = senha
        self.tipo = tipo
        self.destinatario = nome  # Define automaticamente

#Modelo de encomenda
class Encomenda(db.Model):
    __tablename__ = "encomenda"  # Nome exato da tabela no Neon

    codigo = db.Column(db.Integer, primary_key=True)  # SERIAL PRIMARY KEY
    nome = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    data_entrega = db.Column(db.Date, nullable=False)
    remetente = db.Column(db.String(50))
    tamanho = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # Relacionado a Usuario

# Modelo de Condomínio
class Condominio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    cep = db.Column(db.String(20), nullable=False)

# Rota inicial - Página de marketing com botão de login/registro
@app.route('/')
def index():
    return render_template('index.html')

# Tela de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo

            if not session.get("flash_login"):  # Evita repetição de mensagens
                flash("Login realizado com sucesso!", "success")
                session["flash_login"] = True  # Marca que a mensagem foi exibida

            return redirect(url_for('painel'))
        else:
            flash("Credenciais inválidas", "danger")

    return render_template('login.html')

# Tela de cadastro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Log para depuração
        print('DEBUG REGISTER FORM:', dict(request.form))
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirma = request.form['confirma_senha']
        # Define tipo padrão se não vier do formulário
        tipo = request.form.get('tipo', 'Condomino')

        # Verificação se senhas coincidem
        if senha != confirma:
            flash("As senhas não coincidem.", "danger")
            return redirect(url_for('register'))

        # Verificação de usuário já existente
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            flash("Já existe um usuário com esse email, favor realize o login com suas credenciais.", "warning")
            return redirect(url_for('register'))

        # Criação do novo usuário
        hash_senha = generate_password_hash(senha)
        novo_usuario = Usuario(nome=nome, email=email, senha=hash_senha, tipo=tipo)
        db.session.add(novo_usuario)
        db.session.commit()

        flash("Cadastro realizado com sucesso!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Rota de redirecionamento para o painel conforme tipo de usuário
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
    elif tipo == 'Dono do prédio':
        return redirect(url_for('painel_dono'))
    else:
        return "Tipo de usuário não reconhecido, favor entre em contato com o administrador do sistema."

# Painel do Zelador
@app.route('/painel/zelador')
def painel_zelador():
    return render_template('painel_zelador.html')

# Painel do Condômino
@app.route('/painel/condomino')
def painel_condomino():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])

    # Busca as encomendas do usuário logado
    encomendas = Encomenda.query.filter_by(usuario_id=usuario.id).all()

    return render_template('painel_condomino.html', usuario=usuario, encomendas=encomendas)

# Painel do Dono do Prédio
@app.route('/painel/dono')
def painel_dono():
    return render_template('painel_dono.html')

# Painel do Administrador
@app.route('/painel/admin')
def painel_admin():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    usuarios = Usuario.query.all()
    return render_template('painel_admin.html', usuarios=usuarios, usuario=usuario)

# Rota para editar usuário (apenas para o administrador)
@app.route('/atualizar_usuario/<int:id>', methods=['POST'])
def atualizar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    # Suporte tanto para JSON quanto para formulário
    if request.is_json:
        data = request.json
        nome = data.get("nome", usuario.nome)
        email = data.get("email", usuario.email)
        tipo = data.get("tipo", usuario.tipo)
        nova_senha = data.get("nova_senha", None)
    else:
        nome = request.form.get("nome", usuario.nome)
        email = request.form.get("email", usuario.email)
        tipo = request.form.get("tipo", usuario.tipo)
        nova_senha = request.form.get("nova_senha", None)
    usuario.nome = nome
    usuario.email = email
    usuario.tipo = tipo
    usuario.destinatario = nome
    if nova_senha:
        usuario.senha = generate_password_hash(nova_senha)
    db.session.commit()
    flash("Usuário atualizado com sucesso!", "success")
    return redirect(url_for('painel_admin'))

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Você saiu da sessão.", "info")
    return redirect(url_for('login'))

# Rota para administração de usuários (exclusiva para administradores)
@app.route('/admin/usuarios')
def admin_usuarios():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuarios = Usuario.query.all()
    return render_template('usuarios_admin.html', usuarios=usuarios)

@app.route('/admin/condominios', methods=['GET', 'POST'])
def admin_condominios():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        nome = request.form.get('nome')
        endereco = request.form.get('endereco')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        cep = request.form.get('cep')
        if not all([nome, endereco, cidade, estado, cep]):
            flash('Preencha todos os campos.', 'danger')
        else:
            novo_condominio = Condominio(nome=nome, endereco=endereco, cidade=cidade, estado=estado, cep=cep)
            db.session.add(novo_condominio)
            db.session.commit()
            flash('Condomínio cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_condominios'))
    condominios = Condominio.query.all()
    return render_template('admin_condominios.html', usuario=usuario, condominios=condominios)

# Editar condomínio
@app.route('/admin/condominios/editar/<int:id>', methods=['POST'])
def editar_condominio(id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    condominio = Condominio.query.get_or_404(id)
    nome = request.form.get('nome')
    endereco = request.form.get('endereco')
    cidade = request.form.get('cidade')
    estado = request.form.get('estado')
    cep = request.form.get('cep')
    if not all([nome, endereco, cidade, estado, cep]):
        flash('Preencha todos os campos para editar.', 'danger')
    else:
        condominio.nome = nome
        condominio.endereco = endereco
        condominio.cidade = cidade
        condominio.estado = estado
        condominio.cep = cep
        db.session.commit()
        flash('Condomínio atualizado com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Excluir condomínio
@app.route('/admin/condominios/excluir/<int:id>', methods=['POST'])
def excluir_condominio(id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    condominio = Condominio.query.get_or_404(id)
    db.session.delete(condominio)
    db.session.commit()
    flash('Condomínio excluído com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

@app.route('/admin/configuracoes')
def admin_configuracoes():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('admin_configuracoes.html', usuario=usuario)

@app.route('/admin/anomalias')
def admin_anomalias():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('admin_anomalias.html', usuario=usuario)

# Inicialização da aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))