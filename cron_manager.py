from crontab import CronTab
import os
from datetime import datetime


# Caminho absoluto para o interpretador Python e para o script
# Isso garante que o cron execute o script corretamente
PYTHON_PATH = os.sys.executable
SCRIPT_PATH = os.path.abspath("gerencia_switch.py")

def _get_comment_id(porta, acao):
    """Cria um identificador único para o comentário do job no cron."""
    return f"SWITCH_MGMT_{porta}_{acao.upper()}"

def agendar_tarefa(dt_execucao, porta, acao, fim=None):
    if fim is None:
        fim = datetime.now()
    """
    Agenda um novo job no crontab do usuário que está executando o Flask.
    
    :param dt_execucao: Objeto datetime de quando a tarefa deve rodar.
    :param porta: Número da porta do switch.
    :param acao: 'bloquear' ou 'liberar'.
    """
    # Remove qualquer tarefa antiga para a mesma porta/ação antes de criar uma nova
    remover_tarefa(porta, acao)

    cron = CronTab(user=True)
    comment_id = _get_comment_id(porta, acao)
    
    data_formatada = fim.strftime("%Y-%m-%d %H:%M")
    
    # Monta o comando que o cron irá executar
    comando = f'{PYTHON_PATH} {SCRIPT_PATH} {porta} {acao} "{data_formatada}"'
    
    job = cron.new(command=comando, comment=comment_id)
    print(f"Fazendo agendamento: {comando}")
    
    # Define a data e hora exatas para a execução
    job.minute.on(dt_execucao.minute)
    job.hour.on(dt_execucao.hour)
    job.day.on(dt_execucao.day)
    job.month.on(dt_execucao.month)
    
    cron.write()
    print(f"Tarefa agendada: {comment_id} para {dt_execucao.strftime('%d/%m/%Y %H:%M')}")

def remover_tarefa(porta, acao):
    """Remove um job do crontab baseado no seu comentário."""
    cron = CronTab(user=True)
    comment_id = _get_comment_id(porta, acao)
    
    # Encontra e remove todos os jobs com o mesmo comentário
    cron.remove_all(comment=comment_id)
    
    cron.write()
    print(f"Tarefa removida: {comment_id}")

def remove_all():
    """Remove todas as tarefas agendadas pela aplicação (comentário SWITCH_MGMT_*)."""
    cron = CronTab(user=True)
    jobs_removidos = 0
    for job in cron:
        if job.comment.startswith('SWITCH_MGMT_'):
            cron.remove(job)
            jobs_removidos += 1
    cron.write()
    print(f"{jobs_removidos} tarefas agendadas foram removidas.")
