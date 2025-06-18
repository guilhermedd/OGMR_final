from dotenv import load_dotenv
import os
import psycopg2
import time
from pysnmp.hlapi import (
    SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
    ObjectType, ObjectIdentity, Integer, setCmd, getCmd
)

load_dotenv()

INTERVALO = 1  # segundo(s)
IP_SWITCH = os.getenv("SWITCH_IP")
COMUNIDADE = os.getenv("SWITCH_COMUNIDADE")


def snmp_get(ip_switch, comunidade, porta_switch):
    oid = f'1.3.6.1.2.1.2.2.1.7.{porta_switch}'
    error_indication, error_status, error_index, var_binds = next(
        getCmd(
            SnmpEngine(),
            CommunityData(comunidade, mpModel=1),
            UdpTransportTarget((ip_switch, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
    )

    if error_indication:
        print(f"❌ Erro SNMP GET: {error_indication}")
        return None
    elif error_status:
        print(f"❌ Erro no status SNMP GET: {error_status.prettyPrint()}")
        return None
    else:
        return int(var_binds[0][1])  # Deve ser 1 (up) ou 2 (down)


def snmp_set(ip_switch, comunidade, porta_switch, estado):
    oid = f'1.3.6.1.2.1.2.2.1.7.{porta_switch}'
    valor = 1 if estado == "up" else 2

    erro_indicador, erro_status, erro_indice, var_binds = next(
        setCmd(
            SnmpEngine(),
            CommunityData(comunidade, mpModel=1),
            UdpTransportTarget((ip_switch, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid), Integer(valor))
        )
    )

    if erro_indicador:
        print(f"❌ Erro: {erro_indicador}")
    elif erro_status:
        print(f"❌ Erro no status: {erro_status.prettyPrint()}")
    else:
        acao = "bloqueada" if estado == "down" else "liberada"
        print(f"✅ Porta {porta_switch} {acao} com sucesso no switch {ip_switch}")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )


def atualizar_block_periodicamente():
    print("🚀 Iniciando processo de sincronização de bloqueios...")

    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT porta, block FROM computadores WHERE porta NOT IN (SELECT porta FROM mestres);")
            resultados = cursor.fetchall()

            for porta, block in resultados:
                estado_atual = snmp_get(IP_SWITCH, COMUNIDADE, porta)
                if estado_atual is None:
                    continue  # erro na consulta SNMP, ignora essa porta

                if block == 1 and estado_atual != 2:
                    snmp_set(IP_SWITCH, COMUNIDADE, porta, "down")
                elif block == 0 and estado_atual != 1:
                    snmp_set(IP_SWITCH, COMUNIDADE, porta, "up")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"❌ Erro ao atualizar bloqueios: {e}")

        time.sleep(INTERVALO)


if __name__ == "__main__":
    atualizar_block_periodicamente()
