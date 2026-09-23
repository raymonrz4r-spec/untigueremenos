"""
Módulo de recolección y extracción de noticias de medios dominicanos.
Consulta feeds RSS en vivo de Google News RD y los principales periódicos locales.
"""

import feedparser
import requests
import urllib.parse
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

# Palabras clave relevantes para pre-filtrar y priorizar noticias de seguridad/DICRIM/PN/bandas
SECURITY_KEYWORDS = [
    "dicrim", "policia", "policía", "abatid", "arrest", "apresad", "delincuen",
    "banda", "crimen", "criminal", "atraco", "atracador", "asalto", "asaltante",
    "disparo", "tiroteo", "enfrentamiento", "intercambio de disparos",
    "prófugo", "profugo", "entregó", "entrego", "entregado", "allanamiento",
    "decomiso", "droga", "microtráfico", "microtrafico", "homicidio", "asesinat",
    "sicari", "patrulla", "agente", "operativo", "teniente", "coronel",
    "general", "cuartel", "destacamento", "justicia", "fiscalía", "fiscalia"
]

RSS_FEEDS = [
    {
        "name": "Google News RD - Seguridad",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '(DICRIM OR "Policia Nacional" OR "Policía Nacional" OR abatido OR "intercambio de disparos" OR "banda criminal" OR atracadores OR prófugo OR allanamiento OR "se entregó") AND (Dominicana OR "Santo Domingo" OR Santiago)'
        ) + "&hl=es-419&gl=DO&ceid=DO:es-419",
        "is_google": True
    },
    {
        "name": "Google News RD - Operativos y Arrestos",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '(detenidos OR arrestados OR apresados OR incautación OR microtráfico) AND ("Policía Nacional" OR DICRIM) AND Dominicana'
        ) + "&hl=es-419&gl=DO&ceid=DO:es-419",
        "is_google": True
    },
    {
        "name": "Diario Libre (Actualidad)",
        "url": "https://www.diariolibre.com/rss/actualidad.xml",
        "is_google": False
    },
    {
        "name": "Diario Libre (Portada)",
        "url": "https://www.diariolibre.com/rss/portada.xml",
        "is_google": False
    },
    {
        "name": "El Día",
        "url": "https://eldia.com.do/feed/",
        "is_google": False
    },
    {
        "name": "Listín Diario (vía Google News)",
        "url": "https://news.google.com/rss/search?q=" + urllib.parse.quote(
            '(DICRIM OR "Policia Nacional" OR tiroteo OR asalto OR allanamiento) site:listindiario.com'
        ) + "&hl=es-419&gl=DO&ceid=DO:es-419",
        "is_google": True
    },
    {
        "name": "Noticias SIN",
        "url": "https://noticiassin.com/feed/",
        "is_google": False
    },
    {
        "name": "Remolacha.net",
        "url": "https://remolacha.net/feed/",
        "is_google": False
    }
]


def clean_html(raw_html: str) -> str:
    """Elimina etiquetas HTML y caracteres de escape."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def parse_date(date_str: str) -> str:
    """Convierte fechas RSS a formato legible estándar."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str[:16]


def is_potentially_relevant(title: str, summary: str = "") -> bool:
    """Verifica si el texto contiene términos asociados a seguridad en RD."""
    text = (title + " " + summary).lower()
    return any(kw in text for kw in SECURITY_KEYWORDS)


def fetch_dominican_news(max_per_feed: int = 25, strict_prefilter: bool = True) -> list[dict]:
    """
    Descarga los feeds de periódicos dominicanos y devuelve una lista deduplicada de noticias.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    seen_titles = set()
    articles = []

    for feed_info in RSS_FEEDS:
        try:
            req = requests.get(feed_info["url"], headers=headers, timeout=8)
            if req.status_code != 200:
                continue

            parsed = feedparser.parse(req.content)
            entries = parsed.entries[:max_per_feed]

            for entry in entries:
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Normalizar título para deduplicar
                norm_title = re.sub(r"[^\w\s]", "", title.lower())
                if norm_title in seen_titles:
                    continue

                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                
                # Filtrar con palabras clave para ahorrar llamadas al LLM si strict_prefilter es True
                if strict_prefilter and not is_potentially_relevant(title, summary):
                    continue

                seen_titles.add(norm_title)

                # Extraer nombre del medio
                source_name = feed_info["name"]
                if feed_info.get("is_google") and entry.get("source", {}).get("title"):
                    source_name = entry["source"]["title"]
                elif " - " in title:
                    # En Google News el medio suele venir al final del título: "Titular - El Nuevo Diario"
                    parts = title.rsplit(" - ", 1)
                    if len(parts) == 2 and len(parts[1]) < 30:
                        title_clean = parts[0]
                        source_name = parts[1]
                        title = title_clean

                articles.append({
                    "id": len(articles) + 1,
                    "title": title,
                    "summary": summary[:280],
                    "link": entry.get("link", "#"),
                    "published": parse_date(entry.get("published", "")),
                    "source": source_name,
                    "raw_feed": feed_info["name"]
                })

        except Exception as e:
            print(f"Error consultando feed {feed_info['name']}: {e}")

    return articles
