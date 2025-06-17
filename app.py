from flask import Flask, render_template
from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime
import time
import threading

load_dotenv()

INTERVALO = 10  # segundos

app = Flask(__name__)

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
    while True:
        try:
            agora = datetime.now()
            conn = get_connection()
            cursor = conn.cursor()

            # BLOQUEAR se estamos dentro do intervalo (inicio <= agora < fim)
            cursor.execute("""
                UPDATE computadores
                SET block = 1
                WHERE inicio <= %s AND fim > %s
            """, (agora, agora))

            # DESBLOQUEAR se já passou do fim
            cursor.execute("""
                UPDATE computadores
                SET block = 0
                WHERE fim < %s AND block = 1
            """, (agora,))

            conn.commit()
            cursor.close()
            conn.close()
            print(f"[{agora.strftime('%Y-%m-%d %H:%M:%S')}] Atualização feita.")
        except Exception as e:
            print(f"Erro ao atualizar: {e}")
        time.sleep(INTERVALO)



@app.route("/")
def index():
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
    thread = threading.Thread(target=atualizar_block_periodicamente, daemon=True)
    thread.start()
    app.run(debug=True)
