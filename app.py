from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
import cron_manager
from concurrent.futures import ThreadPoolExecutor
import subprocess
import asyncio

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

def executar_comando_imediato(porta, acao):
    """Executa o script de gerenciamento do switch imediatamente."""
    try:
        # Usa os mesmos caminhos que o cron_manager para consistência
        python_path = os.sys.executable
        script_path = os.path.abspath("gerencia_switch.py")
        
        comando = [python_path, script_path, str(porta), acao]
        
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE computadores
        SET inicio = %s, fim = %s, block = 1
        WHERE porta = %s
    """, (inicio, fim, porta))
    conn.commit()
    cursor.close()
    conn.close()

    dt_inicio = datetime.fromisoformat(inicio)
    dt_fim = datetime.fromisoformat(fim)
    if inicio > datetime.now().isoformat():
        executar_comando_imediato(porta, 'bloquear')
    else:
        cron_manager.agendar_tarefa(dt_inicio, porta, 'bloquear')
    cron_manager.agendar_tarefa(dt_fim, porta, 'liberar')


def desbloquear_porta(porta):
    """
    Lógica de desbloqueio completamente refeita para ser IMEDIATA.
    """
    print(f"Iniciando processo de DESBLOQUEIO IMEDIATO para a porta {porta}...")

    cron_manager.remover_tarefa(porta, 'liberar')
    executar_comando_imediato(porta, 'liberar')

    # conn = get_connection()
    # cursor = conn.cursor()
    # cursor.execute("""
    #     UPDATE computadores
    #     SET inicio = NULL, fim = NULL, block = 0
    #     WHERE porta = %s
    # """, (porta,))
    # conn.commit()
    # cursor.close()
    # conn.close()
    
    print(f"Processo de desbloqueio para a porta {porta} finalizado.")


def obter_portas_afetadas():
    """Função auxiliar para obter a lista de portas a serem alteradas."""
    conn = get_connection()
    portas_raw = select_query(conn, "SELECT porta FROM computadores WHERE porta NOT IN (SELECT porta FROM mestres)")
    conn.close()
    return [p[0] for p in portas_raw]


def bloquear_todas_portas(inicio, fim):
    portas_para_bloquear = obter_portas_afetadas() 

    # Atualiza tudo de uma vez no banco 
    # conn = get_connection() 
    # cursor = conn.cursor() 
    # cursor.execute("""
    #     UPDATE computadores
    #     SET inicio = %s, fim = %s, block = 1
    #     WHERE porta = ANY(%s)
    # """, (inicio, fim, portas_para_bloquear)) 
    # conn.commit() 
    # cursor.close()
    # conn.close() 

    dt_inicio = datetime.fromisoformat(inicio) 
    dt_fim = datetime.fromisoformat(fim) 
    
    for porta in portas_para_bloquear:
        cron_manager.remover_tarefa(porta, 'bloquear') 
        cron_manager.remover_tarefa(porta, 'liberar')
        cron_manager.agendar_tarefa(dt_inicio, porta, 'bloquear') 
        cron_manager.agendar_tarefa(dt_fim, porta, 'liberar') 


def desbloquear_todas_portas():
    portas = obter_portas_afetadas()

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