from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///usuarios.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do Flask-Mail para Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'seu_email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'sua_senha_do_gmail')

db = SQLAlchemy(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# Modelo de usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Tipos: Administrador, Dono do prédio, Zelador, Condomino
    destinatario = db.Column(db.String(100), nullable=False)  # Destinatário será sempre igual ao nome completo
    condominio_id = db.Column(db.Integer, db.ForeignKey('condominio.id'), nullable=True)  # Novo campo para vincular ao condomínio

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

# Modelo de Perfil de Usuário
class Perfil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)

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
    usuario = Usuario.query.get(session['usuario_id'])
    usuarios = Usuario.query.all()
    return render_template('usuarios_admin.html', usuarios=usuarios, usuario=usuario)

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
    usuarios = Usuario.query.all()  # Para exibir usuários vinculados
    return render_template('admin_condominios.html', usuario=usuario, condominios=condominios, usuarios=usuarios)

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

@app.route('/admin/configuracoes', methods=['GET', 'POST'])
def admin_configuracoes():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        perfil_id = request.form.get('perfil_id')
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        if perfil_id:  # Editar perfil existente
            perfil = Perfil.query.get(perfil_id)
            if perfil:
                perfil.nome = nome
                perfil.descricao = descricao
                db.session.commit()
                flash('Perfil atualizado com sucesso!', 'success')
        else:  # Criar novo perfil
            if Perfil.query.filter_by(nome=nome).first():
                flash('Já existe um perfil com esse nome.', 'danger')
            else:
                novo_perfil = Perfil(nome=nome, descricao=descricao)
                db.session.add(novo_perfil)
                db.session.commit()
                flash('Perfil criado com sucesso!', 'success')
        return redirect(url_for('admin_configuracoes'))
    perfis = Perfil.query.all()
    return render_template('admin_configuracoes.html', usuario=usuario, perfis=perfis)

@app.route('/admin/anomalias')
def admin_anomalias():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('admin_anomalias.html', usuario=usuario)

# Rota para recuperação de senha
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = Usuario.query.filter_by(email=email).first()
        if user:
            token = serializer.dumps(email, salt='reset-password')
            link = url_for('reset_password', token=token, _external=True)
            msg = Message('Redefinição de Senha - Porteiro Digital',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f'Clique no link para redefinir sua senha: {link}'
            try:
                mail.send(msg)
                flash('Um link de redefinição foi enviado para seu e-mail.', 'success')
            except Exception as e:
                flash('Erro ao enviar e-mail. Contate o suporte.', 'danger')
        else:
            flash('E-mail não encontrado.', 'danger')
        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=3600)
    except Exception:
        flash('O link de redefinição é inválido ou expirou.', 'danger')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        nova_senha = request.form['senha']
        user = Usuario.query.filter_by(email=email).first()
        if user:
            user.senha = generate_password_hash(nova_senha)
            db.session.commit()
            flash('Senha redefinida com sucesso!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('forgot_password'))
    return render_template('reset_password.html', token=token)

# Rota para a página de Minhas Encomendas
@app.route('/minhas-encomendas')
def minhas_encomendas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    encomendas_query = Encomenda.query.filter_by(usuario_id=usuario.id)
    busca = request.args.get('busca', '').strip()
    status = request.args.get('status', '').strip()
    data_entrega = request.args.get('data_entrega', '').strip()
    if busca:
        encomendas_query = encomendas_query.filter(
            (Encomenda.nome.ilike(f'%{busca}%')) |
            (Encomenda.descricao.ilike(f'%{busca}%')) |
            (Encomenda.codigo.ilike(f'%{busca}%'))
        )
    if status:
        encomendas_query = encomendas_query.filter_by(status=status)
    if data_entrega:
        encomendas_query = encomendas_query.filter_by(data_entrega=data_entrega)
    encomendas = encomendas_query.all()
    return render_template('minhas_encomendas.html', usuario=usuario, encomendas=encomendas)

# Rota para vincular usuário a condomínio (apenas para administradores)
@app.route('/admin/condominios/vincular_usuario/<int:condominio_id>', methods=['POST'])
def vincular_usuario_condominio(condominio_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('Selecione um usuário para vincular.', 'danger')
        return redirect(url_for('admin_condominios'))
    user = Usuario.query.get(usuario_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin_condominios'))
    user.condominio_id = condominio_id
    db.session.commit()
    flash(f'Usuário {user.nome} vinculado ao condomínio com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Rota para desvincular usuário de condomínio (apenas para administradores)
@app.route('/admin/condominios/desvincular_usuario/<int:condominio_id>/<int:usuario_id>', methods=['POST'])
def desvincular_usuario_condominio(condominio_id, usuario_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    user = Usuario.query.get(usuario_id)
    if not user or user.condominio_id != condominio_id:
        flash('Usuário não encontrado ou não vinculado a este condomínio.', 'danger')
        return redirect(url_for('admin_condominios'))
    user.condominio_id = None
    db.session.commit()
    flash(f'Usuário {user.nome} desvinculado do condomínio com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Inicialização da aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))