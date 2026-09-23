"""
Módulo de base de datos SQLite para persistencia y despliegue en Vercel / Cloud.
Optimizado para:
1. Traer toda la información de las cards y los KPIs en un solo request SQL.
2. Compatibilidad con el entorno Serverless de Vercel (soporte de lectura/escritura en /tmp).
3. Deduplicación instantánea y seguimiento de titulares procesados para 0 llamadas redundantes a Groq.
"""

import sqlite3
import hashlib
import json
import re
import os
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    """
    Determina la ruta de la base de datos SQLite.
    En Vercel Serverless, copia la base de datos incluida a /tmp para permitir lectura y escritura.
    En local, usa directamente data/news_database.db.
    """
    if os.environ.get("VERCEL"):
        tmp_db = Path("/tmp/news_database.db")
        bundled_db = PROJECT_ROOT / "data" / "news_database.db"
        if not tmp_db.exists() and bundled_db.exists():
            try:
                shutil.copy2(bundled_db, tmp_db)
            except Exception as e:
                print(f"Error copiando DB a /tmp en Vercel: {e}")
        return tmp_db

    local_db = PROJECT_ROOT / "data" / "news_database.db"
    local_db.parent.mkdir(parents=True, exist_ok=True)
    return local_db


def compute_title_hash(title: str) -> str:
    """Genera un hash normalizado único para deduplicación instantánea en SQLite."""
    norm = re.sub(r"[^\w\s]", "", (title or "").lower().strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def get_db_connection() -> sqlite3.Connection:
    """Abre conexión a SQLite con configuración optimizada."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Inicializa las tablas e índices si no existen."""
    conn = get_db_connection()
    try:
        with conn:
            # Tabla de incidentes policiales (para las cards, mapa y KPIs)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    title_hash TEXT UNIQUE NOT NULL,
                    summary TEXT,
                    published TEXT,
                    source TEXT,
                    link TEXT,
                    categoria TEXT,
                    arrestados INTEGER DEFAULT 0,
                    abatidos INTEGER DEFAULT 0,
                    entregados INTEGER DEFAULT 0,
                    ubicacion TEXT,
                    lat REAL,
                    lon REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Tabla de seguimiento de todos los titulares procesados (para no repetir llamadas a Groq)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_titles (
                    title_hash TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    is_relevant INTEGER DEFAULT 0,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_hash ON news_incidents(title_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_pub ON news_incidents(published DESC);")
    finally:
        conn.close()


def get_all_incidents() -> list[dict]:
    """
    Obtiene toda la información necesaria para las cards, mapa y KPIs
    en un solo request SQL optimizado.
    """
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT 
                id,
                title,
                summary,
                published,
                source,
                link,
                categoria,
                arrestados,
                abatidos,
                entregados,
                ubicacion,
                lat,
                lon,
                created_at
            FROM news_incidents
            ORDER BY id DESC;
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_dashboard_payload_single_request() -> dict:
    """
    Devuelve en un solo request consolidado:
    - KPIs agregados (total arrestados, abatidos, entregados, total incidentes).
    - Lista completa de incidentes con toda la información de las cards.
    - Timestamp de actualización.
    Ideal para Vercel Edge caching y Streamlit caching (TTL 15 min).
    """
    incidents = get_all_incidents()
    total_arr = sum(it.get("arrestados", 0) for it in incidents)
    total_abat = sum(it.get("abatidos", 0) for it in incidents)
    total_entr = sum(it.get("entregados", 0) for it in incidents)

    return {
        "kpis": {
            "total_arrestados": total_arr,
            "total_abatidos": total_abat,
            "total_entregados": total_entr,
            "total_incidentes": len(incidents)
        },
        "incidents": incidents,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def filter_new_articles(articles: list[dict]) -> list[dict]:
    """
    Compara una lista de artículos contra processed_titles en una sola consulta
    y devuelve ÚNICAMENTE aquellos titulares que NUNCA han sido analizados por Groq.
    """
    if not articles:
        return []

    init_db()
    conn = get_db_connection()
    try:
        hash_map = {}
        for a in articles:
            h = compute_title_hash(a.get("title", ""))
            hash_map[h] = a

        hashes = list(hash_map.keys())
        if not hashes:
            return []

        placeholders = ",".join("?" for _ in hashes)
        cursor = conn.execute(f"SELECT title_hash FROM processed_titles WHERE title_hash IN ({placeholders})", hashes)
        existing_hashes = {row["title_hash"] for row in cursor.fetchall()}

        new_articles = [hash_map[h] for h in hashes if h not in existing_hashes]
        return new_articles
    finally:
        conn.close()


def record_processed_titles(articles: list[dict], relevant_hashes: set[str]) -> None:
    """Registra todos los titulares evaluados para que nunca se vuelvan a enviar a Groq."""
    if not articles:
        return

    init_db()
    conn = get_db_connection()
    try:
        with conn:
            for art in articles:
                h = compute_title_hash(art.get("title", ""))
                is_rel = 1 if h in relevant_hashes else 0
                conn.execute("""
                    INSERT OR IGNORE INTO processed_titles (title_hash, title, is_relevant)
                    VALUES (?, ?, ?);
                """, (h, art.get("title", ""), is_rel))
    finally:
        conn.close()


def insert_incidents(incidents: list[dict]) -> int:
    """Inserta una lista de incidentes analizados en SQLite y los registra como procesados."""
    if not incidents:
        return 0

    init_db()
    conn = get_db_connection()
    inserted_count = 0
    try:
        with conn:
            for item in incidents:
                t_hash = compute_title_hash(item.get("title", ""))
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO news_incidents (
                            title,
                            title_hash,
                            summary,
                            published,
                            source,
                            link,
                            categoria,
                            arrestados,
                            abatidos,
                            entregados,
                            ubicacion,
                            lat,
                            lon
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        item.get("title", ""),
                        t_hash,
                        item.get("summary", ""),
                        item.get("published", ""),
                        item.get("source", "Medio Dominicano"),
                        item.get("link", "#"),
                        item.get("categoria", "POLICIA_NACIONAL"),
                        int(item.get("arrestados", 0)),
                        int(item.get("abatidos", 0)),
                        int(item.get("entregados", 0)),
                        item.get("ubicacion", "República Dominicana"),
                        float(item.get("lat", 18.7357)),
                        float(item.get("lon", -70.1627))
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    continue
        return inserted_count
    finally:
        conn.close()


def migrate_existing_cache_to_sqlite() -> int:
    """Migra datos desde news_cache.json si existe hacia SQLite para no perder el histórico."""
    cache_file = PROJECT_ROOT / "data" / "news_cache.json"
    if not cache_file.exists():
        return 0

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        if isinstance(items, list) and items:
            inserted = insert_incidents(items)
            rel_hashes = {compute_title_hash(it.get("title", "")) for it in items}
            record_processed_titles(items, rel_hashes)
            return inserted
    except Exception as e:
        print(f"Error migrando caché a SQLite: {e}")
    return 0


# Inicializar automáticamente al importar
init_db()
migrate_existing_cache_to_sqlite()
