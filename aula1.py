import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple


class Tarefa(NamedTuple):
    nome: str
    duracao: float  # tempo de espera simulado, em segundos


TAREFAS: tuple[Tarefa, ...] = (
    Tarefa("Consulta ao sensor", 1.0),
    Tarefa("Leitura do banco de dados", 2.0),
    Tarefa("Envio do relatório", 1.5),
    Tarefa("Download de arquivo", 2.5),
    Tarefa("Chamada à API externa", 1.2),
    Tarefa("Gravação de logs", 0.8),
    Tarefa("Sincronização com a nuvem", 3.0),
    Tarefa("Envio de notificação", 0.5),
    Tarefa("Envio de dados interno", 5.0),
)

# Evita que linhas impressas por threads diferentes se misturem.
_lock_print = threading.Lock()


def log(mensagem: str) -> None:
    with _lock_print:
        print(mensagem, flush=True)


def executar_tarefa(tarefa: Tarefa) -> str:
    """Simula uma operação de E/S e devolve o resultado."""
    thread = threading.current_thread().name
    log(f"[{thread}] Iniciou: {tarefa.nome} ({tarefa.duracao:.1f} s)")
    time.sleep(tarefa.duracao)  # Simula E/S sem ocupar a CPU.
    log(f"[{thread}] Finalizou: {tarefa.nome}")
    return f"{tarefa.nome}: concluída"


def _worker(indice: int, tarefa: Tarefa, resultados: list[str | None]) -> None:
    """Envolve a tarefa para que erros não sumam silenciosamente na thread."""
    try:
        # Cada thread grava só na sua própria posição: não há conflito.
        resultados[indice] = executar_tarefa(tarefa)
    except Exception as erro:
        log(f"[{threading.current_thread().name}] ERRO em {tarefa.nome}: {erro!r}")
        resultados[indice] = f"{tarefa.nome}: FALHOU ({erro})"


def executar_sequencial() -> tuple[float, list[str]]:
    inicio = time.perf_counter()
    resultados = [executar_tarefa(t) for t in TAREFAS]
    return time.perf_counter() - inicio, resultados


def executar_com_threads() -> tuple[float, list[str | None]]:
    resultados: list[str | None] = [None] * len(TAREFAS)
    inicio = time.perf_counter()

    # Criar: cada thread recebe os dados da própria tarefa.
    threads = [
        threading.Thread(
            target=_worker,
            args=(i, tarefa, resultados),
            name=f"Thread-{i + 1}",
        )
        for i, tarefa in enumerate(TAREFAS)
    ]

    # Iniciar todas antes de esperar: permite sobreposição das tarefas.
    for thread in threads:
        thread.start()

    # Aguardar todas: os resultados só estão prontos após os join().
    for thread in threads:
        thread.join()

    return time.perf_counter() - inicio, resultados


def executar_com_pool() -> tuple[float, list[str]]:
    """Forma recomendada: o executor gerencia criação, join e resultados."""
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(TAREFAS), thread_name_prefix="Pool") as pool:
        # map preserva a ordem original e relança exceções ao iterar.
        resultados = list(pool.map(executar_tarefa, TAREFAS))
    return time.perf_counter() - inicio, resultados


def mostrar_resultados(resultados: list[str | None]) -> None:
    for resultado in resultados:
        print(f"  - {resultado}")


def main() -> None:
    print("\n=== EXECUÇÃO SEQUENCIAL ===")
    tempo_seq, res_seq = executar_sequencial()
    print(f"Tempo sequencial: {tempo_seq:.2f} s")
    mostrar_resultados(res_seq)

    print("\n=== EXECUÇÃO COM THREADS ===")
    tempo_thr, res_thr = executar_com_threads()
    print(f"Tempo com threads: {tempo_thr:.2f} s")
    mostrar_resultados(res_thr)

    print("\n=== EXECUÇÃO COM ThreadPoolExecutor ===")
    tempo_pool, res_pool = executar_com_pool()
    print(f"Tempo com pool: {tempo_pool:.2f} s")
    mostrar_resultados(res_pool)

    if tempo_thr > 0:
        print(f"\nGanho (sequencial / threads): {tempo_seq / tempo_thr:.2f}x")
    if tempo_pool > 0:
        print(f"Ganho (sequencial / pool):    {tempo_seq / tempo_pool:.2f}x")
    print(
        "\nObservação: as tarefas são limitadas por E/S, não por CPU. "
        "O tempo total com threads tende ao da tarefa mais longa "
        f"({max(t.duracao for t in TAREFAS):.1f} s)."
    )


if __name__ == "__main__":
    main()