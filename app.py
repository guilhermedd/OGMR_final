from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
import cron_manager
import subprocess

load_dotenv()

app = Flask(__name__)

# --- COMANDOS UTEIS ---

def obter_ip_cliente():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    else:
        ip = request.remote_addr
    return ip

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )

def select_query(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results

def executar_comando_imediato(porta, acao, fim=None):
    """Executa o script de gerenciamento do switch imediatamente."""
    if fim is None:
        fim = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        # Usa os mesmos caminhos que o cron_manager para consistência
        python_path = os.sys.executable
        script_path = os.path.abspath("gerencia_switch.py")
        
        comando = [python_path, script_path, str(porta), acao, fim]
        
        print(f"Executando comando imediato: {' '.join(comando)}")
        
        # Usamos subprocess.run para executar o comando
        subprocess.run(comando, check=True, timeout=10) # Timeout de 10s
        
        print(f"Comando imediato para porta {porta} executado com sucesso.")
        return True
    except Exception as e:
        print(f"ERRO na execução imediata para porta {porta}: {e}")
        return False


# --- LÓGICA DE NEGÓCIO ---

def bloquear_porta(porta, inicio, fim):
    if isinstance(inicio, str):
        inicio = inicio.replace('T', ' ')
        dt_inicio = datetime.strptime(inicio, "%Y-%m-%d %H:%M")
    else:
        dt_inicio = inicio

    if isinstance(fim, str):
        fim = fim.replace('T', ' ')
        dt_fim = datetime.strptime(fim, "%Y-%m-%d %H:%M")
    else:
        dt_fim = fim

    inicio_str = dt_inicio.strftime("%Y-%m-%d %H:%M")
    fim_str = dt_fim.strftime("%Y-%m-%d %H:%M")

    conn = get_connection()
    cursor = conn.cursor()
    block = 1 if dt_inicio < datetime.now() else 0
    cursor.execute("""
        UPDATE computadores
        SET inicio = %s, fim = %s, block = %s
        WHERE porta = %s
    """, (inicio_str, fim_str, block, porta))
    conn.commit()
    cursor.close()
    conn.close()

    # Compara datas
    if dt_inicio < datetime.now():
        print(f"Comando ja começou? {dt_inicio < datetime.now()} | {dt_inicio} < {datetime.now()}")
        print(f"Executando bloqueio imediato da porta {porta} para {dt_inicio} e desbloqueio para {dt_fim} | agora {datetime.now()}")
        executar_comando_imediato(porta, 'bloquear', fim=dt_fim)
    else:
        cron_manager.agendar_tarefa(dt_inicio, porta, 'bloquear', dt_fim)
    cron_manager.agendar_tarefa(dt_fim, porta, 'liberar')


def desbloquear_porta(porta):
    """
    Lógica de desbloqueio completamente refeita para ser IMEDIATA.
    """
    print(f"Iniciando processo de DESBLOQUEIO IMEDIATO para a porta {porta}...")

    cron_manager.remover_tarefa(porta, 'liberar')
    cron_manager.remover_tarefa(porta, 'bloquear')
    executar_comando_imediato(porta, 'liberar')

    print(f"Processo de desbloqueio para a porta {porta} finalizado.")


def obter_portas_afetadas(blocked=False):
    """Função auxiliar para obter a lista de portas a serem alteradas."""
    conn = get_connection()
    if blocked:
        portas_raw = select_query(conn, "SELECT porta FROM computadores WHERE block = 1")
    else:
        portas_raw = select_query(conn, "SELECT porta FROM computadores WHERE porta NOT IN (SELECT porta FROM mestres)")
    conn.close()
    return [p[0] for p in portas_raw]


def bloquear_todas_portas(inicio, fim):
    portas_para_bloquear = obter_portas_afetadas() 
    cron_manager.remove_all()
    
    for porta in portas_para_bloquear:
        bloquear_porta(porta, inicio, fim)


def desbloquear_todas_portas():
    portas = obter_portas_afetadas(blocked=True)

    for porta in portas:
        desbloquear_porta(porta)
        
        
# --- ROTAS FLASK (sem alterações necessárias no corpo das rotas) ---

@app.route('/desbloquear_todos', methods=['GET', 'POST'])
def desbloquear_todos():
    desbloquear_todas_portas()
    return redirect('/')

@app.route('/bloquear', methods=['GET', 'POST'])
def bloquear():
    if request.method == 'POST':
        porta = request.form['porta']
        inicio = request.form['inicio']
        fim = request.form['fim']
        bloquear_porta(porta, inicio, fim)
        return redirect('/')
    else:
        porta = request.args.get('porta')
        return render_template('bloquear.html', porta=porta)

@app.route('/bloquear_todos', methods=['GET', 'POST'])
def bloquear_todos():
    if request.method == 'POST':
        inicio = request.form['inicio']
        fim = request.form['fim']
        bloquear_todas_portas(inicio, fim)
        return redirect('/')
    return render_template('bloquear_todos.html')

@app.route('/desbloquear', methods=['POST'])
def desbloquear():
    porta = request.form['porta']
    desbloquear_porta(porta)
    return redirect('/')

@app.route("/")
def index():
    ip_cliente = obter_ip_cliente()
    with open("professores.txt") as f:
        ips_permitidos = [linha.strip() for linha in f if linha.strip()]

    if ip_cliente not in ips_permitidos:
        return render_template("proibido.html"), 403

    conn = get_connection()
    computadores = select_query(conn, "SELECT porta, block, inicio, fim FROM computadores ORDER BY porta")
    mestres = select_query(conn, "SELECT porta FROM mestres")
    conn.close()
    
    return render_template(
        "index.html",
        computadores=computadores,
        agora=datetime.now(),
        mestres=[m[0] for m in mestres]
    )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')