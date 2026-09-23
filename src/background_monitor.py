"""
Monitor en segundo plano que revisa periódicamente las noticias cada 5 minutos.
Si hay titulares nuevos, los procesa con Groq y los guarda en SQLite.
Si no hay titulares nuevos, NO hace nada (0 consumo de tokens).
"""

import threading
import time
from datetime import datetime
from src.news_scraper import fetch_dominican_news
from src.database import filter_new_articles, insert_incidents, record_processed_titles, compute_title_hash
from src.ai_extractor import NewsAiExtractor

# Variables de control del hilo en segundo plano
_MONITOR_THREAD = None
_MONITOR_RUNNING = False
_LAST_CHECK_TIME = None
_STATUS_INFO = {
    "last_check": None,
    "last_new_count": 0,
    "total_checks": 0,
    "is_active": False
}


def check_and_update_news():
    """
    Ejecuta un ciclo de revisión:
    1. Obtiene las noticias recientes de RD.
    2. Filtra contra SQLite (processed_titles) para ver si hay titulares que nunca se hayan evaluado.
    3. Si NO hay titulares nuevos, termina sin llamar a Groq.
    4. Si hay titulares nuevos, procesa SOLO los nuevos con Groq y los guarda en SQLite.
    """
    global _STATUS_INFO, _LAST_CHECK_TIME
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _LAST_CHECK_TIME = now_str
    _STATUS_INFO["total_checks"] += 1
    _STATUS_INFO["last_check"] = now_str

    try:
        # 1. Obtener titulares de los feeds
        raw_news = fetch_dominican_news(max_per_feed=25, strict_prefilter=True)
        if not raw_news:
            _STATUS_INFO["last_new_count"] = 0
            return 0

        # 2. Comprobar contra SQLite en una sola consulta
        new_articles = filter_new_articles(raw_news)

        if not new_articles:
            # Requisito clave: No hacer nada si no hay titulares nuevos
            print(f"[{now_str}] [Monitor 5m] No hay titulares nuevos. 0 llamadas a Groq.")
            _STATUS_INFO["last_new_count"] = 0
            return 0

        # 3. Procesar ÚNICAMENTE los artículos nuevos con Groq
        print(f"[{now_str}] [Monitor 5m] Se detectaron {len(new_articles)} titulares nuevos. Procesando con Groq...")
        extractor = NewsAiExtractor()
        analyzed = []
        batch_size = 5
        for i in range(0, len(new_articles), batch_size):
            batch = new_articles[i:i + batch_size]
            results = extractor.analyze_batch(batch)
            analyzed.extend(results)

        # 4. Guardar relevantes en SQLite
        inserted = 0
        if analyzed:
            inserted = insert_incidents(analyzed)
            print(f"[{now_str}] [Monitor 5m] Insertados {inserted} incidentes relevantes en SQLite.")

        # 5. Registrar TODOS los evaluados (relevantes o no) para no volver a gastar tokens en ellos
        rel_hashes = {compute_title_hash(a.get("title", "")) for a in analyzed}
        record_processed_titles(new_articles, rel_hashes)

        _STATUS_INFO["last_new_count"] = inserted
        return inserted

    except Exception as e:
        print(f"[{now_str}] [Monitor 5m] Error en ciclo de revisión: {e}")
        return 0


def _monitor_loop(interval_seconds: int = 300):
    """Bucle del monitor que corre cada 5 minutos (300 segundos)."""
    global _MONITOR_RUNNING
    print(f"[Monitor] Hilo activo. Verificando noticias cada {interval_seconds // 60} minutos...")

    # Revisión inicial
    try:
        check_and_update_news()
    except Exception as e:
        print(f"[Monitor] Error en revisión inicial: {e}")

    while _MONITOR_RUNNING:
        time.sleep(interval_seconds)
        if not _MONITOR_RUNNING:
            break
        try:
            check_and_update_news()
        except Exception as e:
            print(f"[Monitor] Error en ciclo periódico: {e}")


def start_background_monitor(interval_seconds: int = 300):
    """Inicia el monitor en segundo plano si aún no está en ejecución."""
    global _MONITOR_THREAD, _MONITOR_RUNNING, _STATUS_INFO
    if _MONITOR_RUNNING and _MONITOR_THREAD and _MONITOR_THREAD.is_alive():
        return

    _MONITOR_RUNNING = True
    _STATUS_INFO["is_active"] = True
    _MONITOR_THREAD = threading.Thread(
        target=_monitor_loop,
        args=(interval_seconds,),
        daemon=True,
        name="NewsBackgroundMonitor"
    )
    _MONITOR_THREAD.start()
    print("[Monitor] Hilo en segundo plano activado exitosamente.")


def get_monitor_status() -> dict:
    """Devuelve el estado del monitor para mostrar en la interfaz."""
    global _STATUS_INFO, _MONITOR_RUNNING
    _STATUS_INFO["is_active"] = _MONITOR_RUNNING
    return _STATUS_INFO
