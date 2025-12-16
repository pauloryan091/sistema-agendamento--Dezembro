from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
import sqlite3
import os
from datetime import datetime
import smtplib
from email.message import EmailMessage
import ssl
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, template_folder='.', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta_aqui_123456')

# Configurações do banco de dados
DATABASE = 'banco.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        
        # Tabela de usuários
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de clientes
        conn.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de serviços
        conn.execute('''    
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                imagem TEXT,
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de agendamentos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                servico_id INTEGER,
                data_agendamento DATE NOT NULL,
                hora_agendamento TIME NOT NULL,
                status TEXT DEFAULT 'pendente',
                usuario_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                FOREIGN KEY (servico_id) REFERENCES servicos (id),
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        conn.commit()
        conn.close()

# Inicializar banco de dados
init_db()

# =====================
# FUNÇÃO DE ENVIO DE EMAIL
# =====================

def enviar_email_gmail(cliente_email, cliente_nome, servico_nome, data_agendamento, hora_agendamento, status):
    """
    Envia email de notificação de agendamento usando Gmail
    """
    try:
        # CONFIGURAÇÃO DO EMAIL DO AGENDAMENTO+
        SEU_EMAIL = os.getenv('EMAIL_USER', 'agendamentomais.suporte1@gmail.com')
        SENHA_APP = os.getenv('EMAIL_PASSWORD', 'tffc icac kqfs igdf')
        
        if not SENHA_APP or SENHA_APP == "digite_aqui_a_senha_de_app":
            print("❌ ERRO CRÍTICO: SENHA DO GMAIL NÃO CONFIGURADA!")
            return False, "Senha do Gmail não configurada"
        
        if not cliente_email:
            print(f"⚠️ Cliente {cliente_nome} não tem email cadastrado")
            return False, "Cliente sem email"
        
        if "@" not in cliente_email or "." not in cliente_email:
            print(f"⚠️ Email inválido: {cliente_email}")
            return False, "Email inválido"
        
        # Converter data para formato brasileiro
        try:
            data_obj = datetime.strptime(data_agendamento, '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d/%m/%Y')
        except:
            data_formatada = data_agendamento
        
        print(f"📧 Enviando email para: {cliente_email}")
        print(f"📤 Status: {status}")
        
        # Criar mensagem
        msg = EmailMessage()
        
        # Definir assunto baseado no status
        if status == 'pendente':
            msg['Subject'] = f'Confirmação de Agendamento - {servico_nome}'
        else:
            msg['Subject'] = f'Atualização do Agendamento - {servico_nome}'
        
        msg['From'] = f'Agendamento+ <{SEU_EMAIL}>'
        msg['To'] = cliente_email
        
        # Mensagens personalizadas por status
        if status == 'pendente':
            mensagem_titulo = "Aguardando Confirmação"
            mensagem_corpo = f"""
            <p>Seu agendamento está <strong>PENDENTE</strong>. Entre em contato conosco para confirmar.</p>
            <p><strong>Urgente:</strong> Precisamos da sua confirmação para garantir seu horário.</p>
            """
            cor_status = '#ffc107'
            cor_texto = '#212529'
            
        elif status == 'confirmado':
            mensagem_titulo = "Agendamento Confirmado!"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>CONFIRMADO</strong>. Estamos esperando por você!</p>
            <p><strong>Importante:</strong> Chegue com 10 minutos de antecedência.</p>
            """
            cor_status = '#17a2b8'
            cor_texto = 'white'
            
        elif status == 'realizado':
            mensagem_titulo = "Agendamento Realizado"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>REALIZADO</strong> com sucesso!</p>
            <p><strong>Obrigado por confiar em nós!</strong> Esperamos ter atendido suas expectativas.</p>
            """
            cor_status = '#28a745'
            cor_texto = 'white'
            
        elif status == 'cancelado':
            mensagem_titulo = "Agendamento Cancelado"
            mensagem_corpo = f"""
            <p>Seu agendamento foi <strong>CANCELADO</strong>.</p>
            <p>Entre em contato conosco para mais informações ou para reagendar.</p>
            """
            cor_status = '#dc3545'
            cor_texto = 'white'
        else:
            mensagem_titulo = "Atualização do Agendamento"
            mensagem_corpo = f"<p>Seu agendamento foi atualizado para: <strong>{status.upper()}</strong></p>"
            cor_status = '#6c757d'
            cor_texto = 'white'
        
        # HTML do email
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agendamento+ - Atualização</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: 700;
            margin: 0;
        }}
        
        .logo span {{
            color: #ffd700;
        }}
        
        .tagline {{
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .status-badge {{
            background: {cor_status};
            color: {cor_texto};
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: 600;
            display: inline-block;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        
        .info-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            border-left: 5px solid #007bff;
        }}
        
        .info-item {{
            display: flex;
            margin: 10px 0;
            padding: 5px 0;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }}
        
        .info-label {{
            font-weight: 600;
            min-width: 120px;
            color: #343a40;
        }}
        
        .info-value {{
            color: #555;
        }}
        
        .message-box {{
            background: rgba(0, 123, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border: 2px solid #007bff;
        }}
        
        .contact-section {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 10px;
        }}
        
        .contact-buttons {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
        }}
        
        .contact-btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: white;
            border-radius: 8px;
            text-decoration: none;
            color: #343a40;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .contact-btn.instagram {{
            border: 2px solid #E4405F;
            color: #E4405F;
        }}
        
        .contact-btn.whatsapp {{
            border: 2px solid #25D366;
            color: #25D366;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #eee;
            background: #f8f9fa;
        }}
        
        @media (max-width: 600px) {{
            .container {{
                margin: 10px;
            }}
            
            .contact-buttons {{
                flex-direction: column;
                align-items: center;
            }}
            
            .contact-btn {{
                width: 100%;
                max-width: 250px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Agendamento<span>+</span></div>
            <p class="tagline">Sistema de Agendamento Online </p>
        </div>
        
        <div class="content">
            <div class="status-badge">
                {status.upper()}
            </div>
            
            <h2 style="color: #343a40; margin-top: 0;">Olá, {cliente_nome}!</h2>
            <p style="color: #666;">Seu agendamento foi atualizado:</p>
            
            <div class="message-box">
                <h3 style="margin-top: 0; color: #007bff;">{mensagem_titulo}</h3>
                {mensagem_corpo}
            </div>
            
            <div class="info-card">
                <div class="info-item">
                    <span class="info-label">Serviço:</span>
                    <span class="info-value">{servico_nome}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Data:</span>
                    <span class="info-value">{data_formatada}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Hora:</span>
                    <span class="info-value">{hora_agendamento}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value" style="color: {cor_status}; font-weight: 600;">{status.upper()}</span>
                </div>
            </div>
            
            <div class="contact-section">
                <p style="margin-bottom: 15px; color: #666;">Em caso de dúvidas, entre em contato conosco:</p>
                
                <div class="contact-buttons">
                    <a href="https://www.instagram.com/agendamentomais/" target="_blank" class="contact-btn instagram">
                        <i class="fab fa-instagram"></i>
                        <span>Instagram</span>
                    </a>
                    <a href="https://wa.me/5561985825956" target="_blank" class="contact-btn whatsapp">
                        <i class="fab fa-whatsapp"></i>
                        <span>WhatsApp</span>
                    </a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p style="margin: 0 0 10px 0; font-weight: 600;">© 2025 Agendamento+. Todos os direitos reservados.</p>
            <p style="margin: 0; color: #999;">
                Esta é uma mensagem automática do sistema Agendamento+.
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        # Versão texto simples
        if status == 'pendente':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento está PENDENTE de confirmação.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

URGENTE: Entre em contato conosco para confirmar seu horário.

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'confirmado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi CONFIRMADO!

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Importante: Chegue com 10 minutos de antecedência.

Estamos esperando por você!

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'realizado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi marcado como REALIZADO!

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Obrigado por confiar em nós!

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        elif status == 'cancelado':
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi CANCELADO.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}

Entre em contato conosco para mais informações.

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        else:
            mensagem_texto = f"""Olá {cliente_nome},

Seu agendamento foi atualizado.

Detalhes:
Serviço: {servico_nome}
Data: {data_formatada}
Hora: {hora_agendamento}
Status: {status.upper()}

Instagram: @agendamentomais
WhatsApp: (61) 98582-5956"""
        
        # Adicionar conteúdo
        msg.set_content(mensagem_texto)
        msg.add_alternative(html, subtype='html')
        
        # Enviar email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(SEU_EMAIL, SENHA_APP)
            server.send_message(msg)
        
        print(f"✅ Email enviado para {cliente_email}")
        return True, "Email enviado com sucesso"
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ ERRO DE AUTENTICAÇÃO: {str(e)}")
        return False, "Erro de autenticação no Gmail"
        
    except Exception as e:
        print(f"❌ Erro ao enviar email: {str(e)}")
        return False, str(e)

# =====================
# ROTAS PRINCIPAIS (PÁGINAS HTML)
# =====================

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/cadastro')
def cadastro_page():
    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/servicos')
def servicos():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('servicos.html')

@app.route('/clientes')
def clientes():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('clientes.html')

@app.route('/agendamentos')
def agendamentos():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('agendamentos.html')

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('perfil.html')

# =====================
# API - AUTENTICAÇÃO
# =====================

@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    try:
        data = request.get_json()
        nome = data.get('nome')
        email = data.get('email')
        senha = data.get('senha')
        
        if not nome or not email or not senha:
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
        
        conn = get_db_connection()
        
        # Verificar se email já existe
        usuario_existente = conn.execute(
            'SELECT id FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        
        if usuario_existente:
            conn.close()
            return jsonify({'success': False, 'message': 'Email já cadastrado'})
        
        # Inserir novo usuário
        conn.execute(
            'INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)',
            (nome, email, senha)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Cadastro realizado com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro no servidor: {str(e)}'})

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        senha = data.get('senha')
        
        conn = get_db_connection()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha)
        ).fetchone()
        conn.close()
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            return jsonify({'success': True, 'message': 'Login realizado com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Email ou senha incorretos'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro no servidor: {str(e)}'})

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso!'})

# =====================
# API - SERVIÇOS
# =====================

@app.route('/api/servicos', methods=['GET', 'POST'])
def api_servicos():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    if request.method == 'GET':
        servicos = conn.execute(
            'SELECT * FROM servicos WHERE usuario_id = ? ORDER BY nome', 
            (usuario_id,)
        ).fetchall()
        conn.close()
        
        servicos_list = []
        for servico in servicos:
            servicos_list.append({
                'id': servico['id'],
                'nome': servico['nome'],
                'descricao': servico['descricao'],
                'imagem': servico['imagem']
            })
        
        return jsonify(servicos_list)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            nome = data.get('nome')
            descricao = data.get('descricao')
            imagem = data.get('imagem')
            
            if not nome:
                return jsonify({'success': False, 'message': 'Nome é obrigatório'})
            
            conn.execute(
                'INSERT INTO servicos (nome, descricao, imagem, usuario_id) VALUES (?, ?, ?, ?)',
                (nome, descricao, imagem, usuario_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Serviço adicionado com sucesso!'})
        
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': f'Erro ao adicionar serviço: {str(e)}'})

@app.route('/api/servicos/<int:servico_id>', methods=['GET', 'PUT', 'DELETE'])
def api_servico(servico_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    try:
        # Verificar se o serviço pertence ao usuário
        servico = conn.execute(
            'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
            (servico_id, usuario_id)
        ).fetchone()
        
        if not servico:
            conn.close()
            return jsonify({'error': 'Serviço não encontrado'}), 404
        
        if request.method == 'GET':
            servico_data = {
                'id': servico['id'],
                'nome': servico['nome'],
                'descricao': servico['descricao'],
                'imagem': servico['imagem']
            }
            conn.close()
            return jsonify(servico_data)
        
        elif request.method == 'PUT':
            data = request.get_json()
            nome = data.get('nome')
            descricao = data.get('descricao')
            imagem = data.get('imagem')
            
            if not nome:
                return jsonify({'success': False, 'message': 'Nome é obrigatório'})
            
            conn.execute(
                'UPDATE servicos SET nome = ?, descricao = ?, imagem = ? WHERE id = ?',
                (nome, descricao, imagem, servico_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Serviço atualizado com sucesso!'})
        
        elif request.method == 'DELETE':
            conn.execute('DELETE FROM servicos WHERE id = ?', (servico_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Serviço excluído com sucesso!'})
    
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Erro ao processar serviço: {str(e)}'})

# =====================
# API - CLIENTES
# =====================

@app.route('/api/clientes', methods=['GET', 'POST'])
def api_clientes():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    if request.method == 'GET':
        clientes = conn.execute(
            'SELECT * FROM clientes WHERE usuario_id = ? ORDER BY nome', 
            (usuario_id,)
        ).fetchall()
        conn.close()
        
        clientes_list = []
        for cliente in clientes:
            clientes_list.append({
                'id': cliente['id'],
                'nome': cliente['nome'],
                'telefone': cliente['telefone'],
                'email': cliente['email']
            })
        
        return jsonify(clientes_list)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            nome = data.get('nome')
            telefone = data.get('telefone')
            email = data.get('email')
            
            if not nome:
                return jsonify({'success': False, 'message': 'Nome é obrigatório'})
            
            conn.execute(
                'INSERT INTO clientes (nome, telefone, email, usuario_id) VALUES (?, ?, ?, ?)',
                (nome, telefone, email, usuario_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Cliente adicionado com sucesso!'})
        
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': f'Erro ao adicionar cliente: {str(e)}'})

@app.route('/api/clientes/<int:cliente_id>', methods=['PUT', 'DELETE'])
def api_cliente(cliente_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    try:
        # Verificar se o cliente pertence ao usuário
        cliente = conn.execute(
            'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
            (cliente_id, usuario_id)
        ).fetchone()
        
        if not cliente:
            conn.close()
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        if request.method == 'PUT':
            data = request.get_json()
            nome = data.get('nome')
            telefone = data.get('telefone')
            email = data.get('email')
            
            if not nome:
                return jsonify({'success': False, 'message': 'Nome é obrigatório'})
            
            conn.execute(
                'UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ?',
                (nome, telefone, email, cliente_id)
            )
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Cliente atualizado com sucesso!'})
        
        elif request.method == 'DELETE':
            conn.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Cliente excluído com sucesso!'})
    
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Erro ao processar cliente: {str(e)}'})

# =====================
# API - AGENDAMENTOS (COM EMAIL)
# =====================

@app.route('/api/agendamentos', methods=['GET', 'POST'])
def api_agendamentos():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    if request.method == 'GET':
        agendamentos = conn.execute('''
            SELECT a.*, c.nome as cliente_nome, c.telefone as cliente_telefone, 
                   c.email as cliente_email, s.nome as servico_nome, 
                   c.id as cliente_id, s.id as servico_id
            FROM agendamentos a 
            LEFT JOIN clientes c ON a.cliente_id = c.id 
            LEFT JOIN servicos s ON a.servico_id = s.id 
            WHERE a.usuario_id = ? 
            ORDER BY a.data_agendamento DESC, a.hora_agendamento DESC
        ''', (usuario_id,)).fetchall()
        conn.close()
        
        agendamentos_list = []
        for agendamento in agendamentos:
            agendamentos_list.append({
                'id': agendamento['id'],
                'cliente_id': agendamento['cliente_id'],
                'cliente_nome': agendamento['cliente_nome'],
                'cliente_telefone': agendamento['cliente_telefone'],
                'cliente_email': agendamento['cliente_email'],
                'servico_id': agendamento['servico_id'],
                'servico_nome': agendamento['servico_nome'],
                'data_agendamento': agendamento['data_agendamento'],
                'hora_agendamento': agendamento['hora_agendamento'],
                'status': agendamento['status']
            })
        
        return jsonify(agendamentos_list)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            cliente_id = data.get('cliente_id')
            servico_id = data.get('servico_id')
            data_agendamento = data.get('data_agendamento')
            hora_agendamento = data.get('hora_agendamento')
            status = data.get('status', 'pendente')
            
            if not cliente_id or not servico_id or not data_agendamento or not hora_agendamento:
                return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'})
            
            # Verificar se cliente e serviço pertencem ao usuário
            cliente = conn.execute(
                'SELECT * FROM clientes WHERE id = ? AND usuario_id = ?', 
                (cliente_id, usuario_id)
            ).fetchone()
            
            servico = conn.execute(
                'SELECT * FROM servicos WHERE id = ? AND usuario_id = ?', 
                (servico_id, usuario_id)
            ).fetchone()
            
            if not cliente:
                conn.close()
                return jsonify({'success': False, 'message': 'Cliente não encontrado'})
            
            if not servico:
                conn.close()
                return jsonify({'success': False, 'message': 'Serviço não encontrado'})
            
            # Inserir agendamento
            conn.execute(
                'INSERT INTO agendamentos (cliente_id, servico_id, data_agendamento, hora_agendamento, status, usuario_id) VALUES (?, ?, ?, ?, ?, ?)',
                (int(cliente_id), int(servico_id), data_agendamento, hora_agendamento, status, usuario_id)
            )
            conn.commit()
            
            # ========== ENVIAR EMAIL PARA NOVO AGENDAMENTO ==========
            if cliente['email']:
                enviar_email_gmail(
                    cliente['email'],
                    cliente['nome'],
                    servico['nome'],
                    data_agendamento,
                    hora_agendamento,
                    status
                )
            
            conn.close()
            
            return jsonify({'success': True, 'message': 'Agendamento realizado com sucesso! Email enviado.'})
        
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': f'Erro ao criar agendamento: {str(e)}'})

@app.route('/api/agendamentos/<int:agendamento_id>', methods=['PUT', 'DELETE'])
def api_agendamento(agendamento_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    
    try:
        # Buscar dados COMPLETOS do agendamento
        agendamento = conn.execute('''
            SELECT a.*, c.email as cliente_email, c.nome as cliente_nome, 
                   s.nome as servico_nome, c.id as cliente_id, s.id as servico_id
            FROM agendamentos a 
            LEFT JOIN clientes c ON a.cliente_id = c.id 
            LEFT JOIN servicos s ON a.servico_id = s.id 
            WHERE a.id = ? AND a.usuario_id = ?
        ''', (agendamento_id, usuario_id)).fetchone()
        
        if not agendamento:
            conn.close()
            return jsonify({'error': 'Agendamento não encontrado'}), 404
        
        if request.method == 'PUT':
            data = request.get_json()
            status = data.get('status')
            
            if status not in ['pendente', 'confirmado', 'cancelado', 'realizado']:
                conn.close()
                return jsonify({'success': False, 'message': 'Status inválido'})
            
            # Atualizar status
            conn.execute(
                'UPDATE agendamentos SET status = ? WHERE id = ?',
                (status, agendamento_id)
            )
            conn.commit()
            
            # ========== ENVIAR EMAIL AO MUDAR STATUS ==========
            if agendamento['cliente_email']:
                enviar_email_gmail(
                    agendamento['cliente_email'],
                    agendamento['cliente_nome'],
                    agendamento['servico_nome'],
                    agendamento['data_agendamento'],
                    agendamento['hora_agendamento'],
                    status
                )
            
            conn.close()
            
            return jsonify({'success': True, 'message': f'Status atualizado e email enviado!'})
        
        elif request.method == 'DELETE':
            conn.execute('DELETE FROM agendamentos WHERE id = ?', (agendamento_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Agendamento excluído com sucesso!'})
    
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Erro ao processar agendamento: {str(e)}'})

# =====================
# API - DADOS DO USUÁRIO
# =====================

@app.route('/api/usuario')
def api_usuario():
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    return jsonify({
        'id': session['usuario_id'],
        'nome': session['usuario_nome'],
        'email': session['usuario_email']
    })

# =====================
# ROTA PARA SERVIR ARQUIVOS ESTÁTICOS
# =====================

@app.route('/<path:filename>')
def serve_files(filename):
    try:
        return send_from_directory('.', filename)
    except:
        return "Arquivo não encontrado", 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# =====================
# INICIALIZAÇÃO
# =====================

if __name__ == '__main__':
    # Criar diretório static se não existir
    if not os.path.exists('static'):
        os.makedirs('static')
    
    print("=" * 60)
    print("AGENDAMENTO+ - SISTEMA COMPLETO")
    print("=" * 60)
    print("🌐 Servidor: http://localhost:5000")
    print("💾 Banco de dados: banco.db")
    print("📧 Email configurado: agendamentomais.suporte1@gmail.com")
    print("=" * 60)
    print("📱 Redes Sociais:")
    print("   Instagram: @agendamentomais")
    print("   WhatsApp: (61) 98582-5956")
    print("=" * 60)
    print("✅ Sistema pronto para uso!")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)