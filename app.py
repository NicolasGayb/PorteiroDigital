from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
from datetime import datetime
from sqlalchemy import func

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

# Tabela de associação muitos-para-muitos entre Apartamento e Usuario
apartamento_usuario = db.Table('apartamento_usuario',
    db.Column('apartamento_id', db.Integer, db.ForeignKey('apartamento.id'), primary_key=True),
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True)
)

# Modelo de usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Tipos: Administrador, Dono do prédio, Zelador, Condomino
    destinatario = db.Column(db.String(100), nullable=False)  # Destinatário será sempre igual ao nome completo
    condominio_id = db.Column(db.Integer, db.ForeignKey('condominio.id'), nullable=True)  # Só usado para porteiros
    apartamentos = db.relationship('Apartamento', secondary=apartamento_usuario, back_populates='usuarios')

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
    apartamento_id = db.Column(db.Integer, db.ForeignKey('apartamento.id'), nullable=False)  # Relaciona com apartamento
    condominio_id = db.Column(db.Integer, db.ForeignKey('condominio.id'))  # Adicionado se não existir
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuario.id'))    # Porteiro que registrou
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Novo modelo de Apartamento
class Apartamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False)
    bloco = db.Column(db.String(20), nullable=True)
    condominio_id = db.Column(db.Integer, db.ForeignKey('condominio.id'), nullable=False)
    # usuario_id removido
    usuarios = db.relationship('Usuario', secondary=apartamento_usuario, back_populates='apartamentos')

# Modelo de Condomínio
class Condominio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    cep = db.Column(db.String(20), nullable=False)
    porteiros = db.relationship('Usuario', backref='condominio', lazy='dynamic', primaryjoin="and_(Condominio.id==Usuario.condominio_id, Usuario.tipo=='Porteiro')")

# Modelo de Perfil de Usuário
class Perfil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)

# Modelo de Log
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False)
    usuario_nome = db.Column(db.String(100), nullable=False)
    acao = db.Column(db.String(100), nullable=False)
    detalhes = db.Column(db.String(200), nullable=True)

# Modelo de Notificação Enviada
class NotificacaoEnviada(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    usuario_nome = db.Column(db.String(100), nullable=True)
    assunto = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)

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
    if tipo == 'Porteiro':
        return redirect(url_for('painel_porteiro'))
    elif tipo == 'Condomino':
        return redirect(url_for('painel_condomino'))
    elif tipo == 'Administrador':
        return redirect(url_for('painel_admin'))
    elif tipo == 'Dono do prédio':
        return redirect(url_for('painel_dono'))
    else:
        return "Tipo de usuário não reconhecido, favor entre em contato com o administrador do sistema."

# Painel do Zelador
@app.route('/painel/porteiro', methods=['GET', 'POST'])
def painel_porteiro():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    condominio_id = usuario.condominio_id
    if not condominio_id:
        flash('Você não está vinculado a nenhum condomínio. Solicite ao administrador.', 'danger')
        return redirect(url_for('logout'))
    apartamentos = Apartamento.query.filter_by(condominio_id=condominio_id).all()
    if request.method == 'POST':
        apartamento_id = request.form.get('apartamento_id')
        nome = request.form.get('recipient_name')
        descricao = request.form.get('descricao')
        data_entrega = datetime.now().date()
        nova_encomenda = Encomenda(
            nome=nome,
            descricao=descricao,
            data_entrega=data_entrega,
            apartamento_id=apartamento_id,
            condominio_id=condominio_id,
            registrado_por=usuario.id,
            created_at=datetime.now(),
            status='Registrada',
            tamanho='Padrão'  # Ajuste conforme necessário
        )
        db.session.add(nova_encomenda)
        db.session.commit()
        flash('Encomenda registrada com sucesso!', 'success')
        return redirect(url_for('painel_porteiro'))

    # Histórico do porteiro (encomendas registradas por ele)
    entregas = Encomenda.query.filter_by(registrado_por=usuario.id).order_by(Encomenda.created_at.desc()).all()

    # Encomendas do mês atual para o condomínio
    now = datetime.now()
    encomendas_mes = Encomenda.query.filter(
        Encomenda.condominio_id == condominio_id,
        Encomenda.created_at >= datetime(now.year, now.month, 1)
    ).order_by(Encomenda.created_at.desc()).all()

    return render_template(
        'painel_porteiro.html',
        usuario=usuario,
        entregas=entregas,
        encomendas_mes=encomendas_mes,
        apartamentos=apartamentos
    )

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
    usuarios = Usuario.query.all()  # Para exibir usuários
    apartamentos = Apartamento.query.options(db.joinedload(Apartamento.usuarios)).all()  # Apartamentos com usuários
    return render_template('admin_condominios.html', usuario=usuario, condominios=condominios, usuarios=usuarios, apartamentos=apartamentos)

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

# Rota para cadastro de apartamento por condomínio, apenas para administradores
@app.route('/admin/condominios/<int:condominio_id>/cadastrar_apartamento', methods=['POST'])
def cadastrar_apartamento(condominio_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    numero = request.form.get('numero')
    bloco = request.form.get('bloco')
    if not numero:
        flash('Informe o número do apartamento.', 'danger')
        return redirect(url_for('admin_condominios'))
    # Verifica duplicidade
    existe = Apartamento.query.filter_by(condominio_id=condominio_id, numero=numero, bloco=bloco).first()
    if existe:
        flash('Já existe um apartamento com esse número e bloco neste condomínio.', 'danger')
        return redirect(url_for('admin_condominios'))
    novo_ap = Apartamento(numero=numero, bloco=bloco, condominio_id=condominio_id)
    db.session.add(novo_ap)
    db.session.commit()
    flash('Apartamento cadastrado com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Editar apartamento
@app.route('/admin/apartamentos/<int:apartamento_id>/editar', methods=['POST'])
def editar_apartamento(apartamento_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    ap = Apartamento.query.get_or_404(apartamento_id)
    numero = request.form.get('numero')
    bloco = request.form.get('bloco')
    if not numero:
        flash('Informe o número do apartamento.', 'danger')
        return redirect(url_for('admin_condominios'))
    # Verifica duplicidade (exceto o próprio)
    existe = Apartamento.query.filter(
        Apartamento.condominio_id == ap.condominio_id,
        Apartamento.numero == numero,
        Apartamento.bloco == bloco,
        Apartamento.id != ap.id
    ).first()
    if existe:
        flash('Já existe um apartamento com esse número e bloco neste condomínio.', 'danger')
        return redirect(url_for('admin_condominios'))
    ap.numero = numero
    ap.bloco = bloco
    db.session.commit()
    flash('Apartamento atualizado com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

@app.route('/admin/apartamentos/<int:apartamento_id>/excluir', methods=['POST'])
def excluir_apartamento(apartamento_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    ap = Apartamento.query.get_or_404(apartamento_id)
    db.session.delete(ap)
    db.session.commit()
    flash('Apartamento excluído com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

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
    if not user or user.tipo != 'Porteiro':
        flash('Apenas usuários do tipo Porteiro podem ser vinculados.', 'danger')
        return redirect(url_for('admin_condominios'))
    user.condominio_id = condominio_id
    db.session.commit()
    flash(f'Porteiro {user.nome} vinculado ao condomínio com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Rota para desvincular usuário de condomínio (apenas para administradores)
@app.route('/admin/condominios/desvincular_usuario/<int:condominio_id>/<int:usuario_id>', methods=['POST'])
def desvincular_usuario_condominio(condominio_id, usuario_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    user = Usuario.query.get(usuario_id)
    if not user or user.condominio_id != condominio_id or user.tipo != 'Porteiro':
        flash('Porteiro não encontrado ou não vinculado a este condomínio.', 'danger')
        return redirect(url_for('admin_condominios'))
    user.condominio_id = None
    db.session.commit()
    flash(f'Porteiro {user.nome} desvinculado do condomínio com sucesso!', 'success')
    return redirect(url_for('admin_condominios'))

# Rota para registrar encomenda
@app.route('/registrar-encomenda', methods=['GET', 'POST'])
def registrar_encomenda():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    condominio_id = usuario.condominio_id
    apartamentos = Apartamento.query.filter_by(condominio_id=condominio_id).all()
    if request.method == 'POST':
        apartamento_id = request.form.get('apartamento_id')
        nome = request.form.get('recipient_name')
        descricao = request.form.get('descricao')
        data_entrega = datetime.now().date()
        nova_encomenda = Encomenda(
            nome=nome,
            descricao=descricao,
            data_entrega=data_entrega,
            apartamento_id=apartamento_id,
            condominio_id=condominio_id,
            registrado_por=usuario.id,
            created_at=datetime.now(),
            status='Registrada',
            tamanho='Padrão'  # Ajuste conforme necessário
        )
        db.session.add(nova_encomenda)
        db.session.commit()
        flash('Encomenda registrada com sucesso!', 'success')
        return redirect(url_for('painel_porteiro'))
    return render_template('registrar_encomenda.html', usuario=usuario, apartamentos=apartamentos)

# Configuração de notificações globais (simples, usando variáveis em memória para exemplo)
notificacoes_globais = {
    'notificacoes_email': True,
    'notificacoes_encomenda': True,
    'notificacoes_alertas': True
}

def enviar_notificacao_global(assunto, mensagem, usuarios):
    from datetime import datetime
    with app.app_context():
        for user in usuarios:
            try:
                msg = Message(assunto, sender=app.config['MAIL_USERNAME'], recipients=[user.email])
                msg.body = mensagem
                mail.send(msg)
                # Salva histórico de envio
                notificacao = NotificacaoEnviada(
                    data_hora=datetime.now(),
                    usuario_id=user.id,
                    usuario_nome=user.nome,
                    assunto=assunto,
                    mensagem=mensagem
                )
                db.session.add(notificacao)
            except Exception as e:
                print(f"Erro ao enviar e-mail para {user.email}: {e}")
        db.session.commit()

@app.route('/admin/configuracoes', methods=['GET', 'POST'])
def admin_configuracoes():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    global notificacoes_globais
    if request.method == 'POST':
        # Verifica se é submissão do formulário de notificações
        if 'notificacoes_email' in request.form or 'notificacoes_encomenda' in request.form or 'notificacoes_alertas' in request.form:
            notificacoes_globais['notificacoes_email'] = 'notificacoes_email' in request.form
            notificacoes_globais['notificacoes_encomenda'] = 'notificacoes_encomenda' in request.form
            notificacoes_globais['notificacoes_alertas'] = 'notificacoes_alertas' in request.form
            assunto = request.form.get('assunto_notificacao', 'Configuração de Notificações Atualizada')
            mensagem = request.form.get('mensagem_notificacao', 'As preferências globais de notificações da plataforma foram atualizadas pelo administrador.')
            flash('Preferências de notificações atualizadas!', 'success')
            # Envia notificação real se marcado
            if notificacoes_globais['notificacoes_email']:
                usuarios = Usuario.query.all()
                enviar_notificacao_global(
                    assunto,
                    mensagem,
                    usuarios
                )
                flash('Notificações enviadas por e-mail para todos os usuários.', 'info')
        else:
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
    logs = Log.query.order_by(Log.data_hora.desc()).limit(50).all()
    historico_notificacoes = NotificacaoEnviada.query.order_by(NotificacaoEnviada.data_hora.desc()).limit(50).all()
    return render_template(
        'admin_configuracoes.html',
        usuario=usuario,
        perfis=perfis,
        logs=logs,
        notificacoes_email=notificacoes_globais['notificacoes_email'],
        notificacoes_encomenda=notificacoes_globais['notificacoes_encomenda'],
        notificacoes_alertas=notificacoes_globais['notificacoes_alertas'],
        historico_notificacoes=historico_notificacoes
    )

@app.route('/admin/anomalias', methods=['GET', 'POST'])
def admin_anomalias():
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')
    query = Encomenda.query
    if data_inicio:
        query = query.filter(Encomenda.data_entrega >= data_inicio)
    if data_fim:
        query = query.filter(Encomenda.data_entrega <= data_fim)
    encomendas = query.all()
    # Análise simples: apartamentos com mais encomendas que o dobro da média
    total = len(encomendas)
    anomalias = []
    if total > 0:
        # Contagem por apartamento
        from collections import Counter
        contagem = Counter([e.apartamento_id for e in encomendas])
        media = total / len(contagem) if contagem else 0
        for ap_id, qtd in contagem.items():
            if qtd > 2 * media:
                ap = Apartamento.query.get(ap_id)
                anomalias.append({
                    'apartamento': f"{ap.numero}{' - Bloco ' + ap.bloco if ap.bloco else ''}",
                    'qtd': qtd,
                    'media': round(media, 2)
                })
        # Horários incomuns (fora de 7h-22h)
        horarios = [e.created_at for e in encomendas if e.created_at]
        horarios_incomuns = [e for e in encomendas if e.created_at and (e.created_at.hour < 7 or e.created_at.hour > 22)]
    else:
        horarios_incomuns = []
    return render_template('admin_anomalias.html', usuario=usuario, anomalias=anomalias, horarios_incomuns=horarios_incomuns, data_inicio=data_inicio, data_fim=data_fim)

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

# Rota para vincular usuário a apartamento (apenas para administradores)
@app.route('/admin/apartamentos/<int:apartamento_id>/vincular_usuario', methods=['POST'])
def vincular_usuario_apartamento(apartamento_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('Selecione um usuário para vincular.', 'danger')
        return redirect(url_for('admin_condominios'))
    user = Usuario.query.get(usuario_id)
    if not user or user.tipo != 'Condomino':
        flash('Apenas usuários do tipo Condomino podem ser vinculados a apartamentos.', 'danger')
        return redirect(url_for('admin_condominios'))
    ap = Apartamento.query.get(apartamento_id)
    if not ap:
        flash('Apartamento não encontrado.', 'danger')
        return redirect(url_for('admin_condominios'))
    if user not in ap.usuarios:
        ap.usuarios.append(user)
        db.session.commit()
        flash(f'Condomino {user.nome} vinculado ao apartamento com sucesso!', 'success')
    else:
        flash('Usuário já está vinculado a este apartamento.', 'warning')
    return redirect(url_for('admin_condominios'))

@app.route('/admin/apartamentos/<int:apartamento_id>/desvincular_usuario/<int:usuario_id>', methods=['POST'])
def desvincular_usuario_apartamento(apartamento_id, usuario_id):
    if 'usuario_id' not in session or session.get('tipo') != 'Administrador':
        return redirect(url_for('login'))
    ap = Apartamento.query.get_or_404(apartamento_id)
    user = Usuario.query.get(usuario_id)
    if not ap or not user or user.tipo != 'Condomino':
        flash('Condomino não encontrado ou não vinculado a este apartamento.', 'danger')
        return redirect(url_for('admin_condominios'))
    if user in ap.usuarios:
        ap.usuarios.remove(user)
        db.session.commit()
        flash(f'Condomino {user.nome} desvinculado do apartamento com sucesso!', 'success')
    else:
        flash('Usuário não está vinculado a este apartamento.', 'warning')
    return redirect(url_for('admin_condominios'))

# Inicialização da aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))