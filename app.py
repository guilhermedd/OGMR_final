from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
import time
from multiprocessing import Process

load_dotenv()

INTERVALO = 1  # segundo(s)

app = Flask(__name__)

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

def atualizar_block_periodicamente():
    print(f"Verificando bloqueios...")
    while True:
        try:
            agora = datetime.now()

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE computadores
                SET block = 1
                WHERE inicio <= %s AND fim > %s
            """, (agora, agora))

            cursor.execute("""
                UPDATE computadores
                SET block = 0
                WHERE fim < %s AND block = 1
            """, (agora,))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao atualizar: {e}")

        time.sleep(INTERVALO)

def bloquear_porta(porta, inicio, fim):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE computadores
        SET inicio = %s, fim = %s
        WHERE porta = %s
    """, (inicio, fim, porta))
    conn.commit()
    cursor.close()
    conn.close()

def bloquear_todas_portas(inicio, fim):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE computadores
        SET inicio = %s, fim = %s
        WHERE porta NOT IN (SELECT porta FROM mestres)
    """, (inicio, fim))
    conn.commit()
    cursor.close()
    conn.close()

def desbloquear_todas_portas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE computadores
        SET inicio = NULL, fim = NULL, block = 0
        WHERE porta NOT IN (SELECT porta FROM mestres)
    """)
    conn.commit()
    cursor.close()
    conn.close()

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
        return redirect('/')  # Redireciona para a página principal
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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE computadores
        SET inicio = NULL, fim = NULL, block = 0
        WHERE porta = %s
    """, (porta,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route("/")
def index():
    ip_cliente = obter_ip_cliente()
    
    with open("professores.txt") as f:
        ips_permitidos = [linha.strip() for linha in f if linha.strip()]

    if ip_cliente not in ips_permitidos:
        return render_template("proibido.html"), 403

    conn = get_connection()
    query = "SELECT porta, block, inicio, fim FROM computadores ORDER BY porta"
    computadores = select_query(conn, query)
    
    query = "SELECT porta FROM mestres"
    mestres = select_query(conn, query)
    
    agora = datetime.now()
    conn.close()
    
    return render_template(
        "index.html",
        computadores=computadores,
        agora=agora,
        mestres=[m[0] for m in mestres]
    )



if __name__ == "__main__":
    processo = Process(target=atualizar_block_periodicamente)
    processo.daemon = True
    processo.start()
    app.run(debug=True, host='0.0.0.0')

