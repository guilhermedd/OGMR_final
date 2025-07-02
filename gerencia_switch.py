import sys
import subprocess
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
from cron_manager import remover_tarefa

# Carrega variáveis de ambiente do .env
load_dotenv() 

# --- CONFIGURAÇÕES DO SWITCH ---
SWITCH_IP = "10.90.90.90" 
COMMUNITY_WRITE = "private" 
OID_BASE = "1.3.6.1.2.1.2.2.1.7." 
# -------------------------------

def get_connection():
    """Cria conexão com o banco de dados usando variáveis de ambiente.""" 
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    ) 

def atualizar_status_no_banco(porta, acao, fim):
    """Atualiza o campo 'block' e os horários no banco conforme a ação.""" 
    try:
        conn = get_connection() 
        cursor = conn.cursor() 
        if acao == "bloquear":
            cursor.execute("""
                UPDATE computadores
                SET block = 1, inicio = %s, fim = %s
                WHERE porta = %s
            """, (datetime.now().strftime("%Y-%m-%d %H:%M"), fim, porta)) 
        elif acao == "liberar":
            cursor.execute("""
                UPDATE computadores
                SET block = 0, inicio = NULL, fim = NULL
                WHERE porta = %s
            """, (porta,)) 
        conn.commit() 
        cursor.close() 
        conn.close() 
        print(f"Banco de dados atualizado para porta {porta}, ação '{acao}'.") 
    except Exception as e:
        print(f"ERRO ao atualizar o banco para porta {porta}: {e}") 

def gerenciar_porta(porta, acao, fim=datetime.now().strftime("%Y-%m-%d %H:%M")):
    if acao == "bloquear":
        snmp_valor = "2" 
    elif acao == "liberar":
        snmp_valor = "1" 
    else:
        print("Ação inválida. Use 'bloquear' ou 'liberar'.") 
        return 

    oid_completo = OID_BASE + str(porta) 
    comando = [
        "snmpset", "-v2c", "-c", COMMUNITY_WRITE,
        SWITCH_IP, oid_completo, "i", snmp_valor
    ] 
    
    remover_tarefa(porta, acao)
    print("Executando comando:", " ".join(comando))
    try:
        atualizar_status_no_banco(porta, acao, fim=fim)
        subprocess.run(comando, check=True, capture_output=True) 
        print(f"SUCESSO: Porta {porta} ação '{acao}' executada.") 
    except subprocess.CalledProcessError as e:
        print(f"ERRO ao executar para porta {porta}: {e.stderr.decode().strip()}") 

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python gerencia_switch.py <porta> <bloquear|liberar> <fim: 'YYYY-MM-DD HH:MM'>") 
        sys.exit(1) 
    print("Rodando aogra!", sys.argv)

    try:
        porta_arg = int(sys.argv[1]) 
    except ValueError:
        print("Porta deve ser um número inteiro.") 
        sys.exit(1) 

    acao_arg = sys.argv[2].lower()

    try:
        fim_arg = datetime.strptime(sys.argv[3], "%Y-%m-%d %H:%M")
    except ValueError:
        print("Formato de data inválido. Use: 'YYYY-MM-DD HH:MM'")
        sys.exit(1)

    gerenciar_porta(porta_arg, acao_arg, fim=fim_arg)

