"""
Motor de Inteligencia Artificial para filtrado y extracción de métricas policiales.
Utiliza Groq API (openai/gpt-oss-120b) con estructuración JSON y persistencia en caché.
"""

import os
import json
import toml
import re
from pathlib import Path
from groq import Groq
from src.geo_utils import geocode_dominican_location, apply_jitter

# Rutas de almacenamiento
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
CACHE_PATH = PROJECT_ROOT / "data" / "news_cache.json"


def get_groq_api_key() -> str:
    """Obtiene la clave de Groq desde secrets.toml o variables de entorno."""
    # 1. Intentar desde secrets.toml
    if SECRETS_PATH.exists():
        try:
            secrets = toml.load(SECRETS_PATH)
            key = secrets.get("GROQ_API_KEY")
            if key:
                return key.strip()
        except Exception as e:
            print(f"Advertencia al leer secrets.toml: {e}")

    # 2. Intentar variable de entorno
    return os.environ.get("GROQ_API_KEY", "").strip()


def load_news_cache() -> list[dict]:
    """Carga las noticias previamente analizadas desde el archivo de caché."""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando caché: {e}")
    return []


def save_news_cache(news_items: list[dict]) -> None:
    """Guarda las noticias analizadas en el archivo de caché."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(news_items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando caché: {e}")


class NewsAiExtractor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or get_groq_api_key()
        if not self.api_key:
            raise ValueError("No se encontró GROQ_API_KEY en .streamlit/secrets.toml ni en el entorno.")
        self.client = Groq(api_key=self.api_key)
        self.primary_model = "openai/gpt-oss-120b"
        self.fallback_model = "openai/gpt-oss-20b"

    def _call_groq_with_fallback(self, prompt: str) -> str:
        """Envía solicitud a Groq con manejo de fallback de modelo."""
        models_to_try = [self.primary_model, self.fallback_model]
        last_error = None

        for model in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un analista de inteligencia de la Dirección Central de Investigación (DICRIM) "
                                "y la Policía Nacional de República Dominicana. Tu misión es filtrar publicaciones "
                                "y estructurar datos de criminalidad, arrestos, abatidos y entregas en formato JSON con la clave 'noticias'."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=2200
                )
                return response.choices[0].message.content
            except Exception as e:
                last_error = e
                print(f"Error con modelo {model}: {e}. Intentando fallback...")

        raise RuntimeError(f"Falla total al consultar modelos de Groq: {last_error}")

    def analyze_batch(self, raw_articles: list[dict]) -> list[dict]:
        """
        Analiza un lote de noticias en una sola llamada estructurada a Groq.
        Filtra noticias de DICRIM, PN, bandas y extrae métricas de arrestados, abatidos y entregados.
        """
        if not raw_articles:
            return []

        articles_payload = [
            {
                "idx": i,
                "title": art["title"],
                "summary": art.get("summary", "")[:200]
            }
            for i, art in enumerate(raw_articles)
        ]

        prompt = f"""
Evalúa los siguientes artículos de noticias de la República Dominicana.
Filtra ESTRICTAMENTE aquellos que traten sobre:
- DICRIM (Dirección Central de Investigación)
- Policía Nacional de República Dominicana
- Bandas criminales, pandillas, delincuentes, asaltantes, sicarios, prófugos
- Operativos policiales, allanamientos, tiroteos, intercambios de disparos, incautaciones de armas/drogas

Si un artículo NO trata sobre delincuencia, policía, DICRIM o bandas en República Dominicana (por ejemplo: farándula, deportes, política civil general, noticias internacionales de otros países), marca 'es_relevante': false.

Para cada noticia analizada devuelve un objeto dentro de la lista 'noticias' con los siguientes campos EXACTOS:
- idx: número índice original del artículo (0..N-1)
- es_relevante: booleano (true si cumple estrictamente el filtro, false si es irrelevante)
- arrestados: entero con el número de personas arrestadas/detenidas identificadas (0 si ninguna o no se menciona)
- abatidos: entero con el número de delincuentes/sospechosos abatidos o fallecidos en enfrentamientos con autoridades (0 si ninguno)
- entregados: entero con el número de sospechosos o prófugos que se entregaron a las autoridades (0 si ninguno)
- ubicacion: nombre del sector, municipio o provincia de RD donde ocurrieron los hechos (ej: "Santo Domingo Este", "Santiago", "Los Alcarrizos", "Barahona", "La Vega")
- lat: latitud aproximada en República Dominicana (float entre 17.5 y 20.0)
- lon: longitud aproximada en República Dominicana (float entre -72.0 y -68.3)
- resumen: resumen conciso del hecho en español (máximo 2 oraciones claras)
- categoria: una de ['DICRIM', 'POLICIA_NACIONAL', 'BANDA_CRIMINAL', 'OPERATIVO', 'PROFUGO']

Artículos a evaluar:
{json.dumps(articles_payload, ensure_ascii=False)}
"""

        try:
            raw_response = self._call_groq_with_fallback(prompt)
            data = json.loads(raw_response)
            items = data.get("noticias", [])
        except Exception as e:
            print(f"Error procesando lote con IA: {e}")
            return []

        processed_results = []
        for item in items:
            idx = item.get("idx")
            if idx is None or idx < 0 or idx >= len(raw_articles):
                continue

            base_art = raw_articles[idx]
            es_relevante = bool(item.get("es_relevante", False))

            if not es_relevante:
                continue

            # Geocodificación y validación estricta en territorio dominicano
            loc_name = item.get("ubicacion", "República Dominicana")
            lat, lon = geocode_dominican_location(loc_name, item.get("lat"), item.get("lon"))
            # Aplicar dispersión ligera para que puntos en la misma zona se puedan visualizar
            lat_jitter, lon_jitter = apply_jitter(lat, lon)

            # Categoría
            cat = str(item.get("categoria", "POLICIA_NACIONAL")).upper().strip()
            if cat not in ["DICRIM", "POLICIA_NACIONAL", "BANDA_CRIMINAL", "OPERATIVO", "PROFUGO"]:
                if "DICRIM" in base_art["title"].upper():
                    cat = "DICRIM"
                elif "BANDA" in base_art["title"].upper():
                    cat = "BANDA_CRIMINAL"
                elif "OPERATIVO" in base_art["title"].upper() or "ALLANAMIENTO" in base_art["title"].upper():
                    cat = "OPERATIVO"
                else:
                    cat = "POLICIA_NACIONAL"

            processed_results.append({
                "id": base_art.get("id") or len(processed_results) + 1,
                "title": base_art["title"],
                "summary": item.get("resumen") or base_art.get("summary", ""),
                "published": base_art.get("published", ""),
                "source": base_art.get("source", "Medio Dominicano"),
                "link": base_art.get("link", "#"),
                "categoria": cat,
                "arrestados": int(item.get("arrestados", 0)),
                "abatidos": int(item.get("abatidos", 0)),
                "entregados": int(item.get("entregados", 0)),
                "ubicacion": loc_name,
                "lat": lat_jitter,
                "lon": lon_jitter,
                "lat_base": lat,
                "lon_base": lon
            })

        return processed_results

    def process_all_news(self, articles: list[dict], batch_size: int = 6) -> list[dict]:
        """
        Procesa una lista completa de noticias en pequeños lotes para evitar límites de tokens.
        Aprovecha el caché local para no reprocesar noticias ya analizadas.
        """
        cached_items = load_news_cache()
        cached_links = {item["link"] for item in cached_items if "link" in item}
        cached_titles = {re.sub(r"[^\w\s]", "", item["title"].lower()) for item in cached_items if "title" in item}

        new_articles_to_process = []
        for art in articles:
            norm_title = re.sub(r"[^\w\s]", "", art["title"].lower())
            if art.get("link") in cached_links or norm_title in cached_titles:
                continue
            new_articles_to_process.append(art)

        print(f"Noticias nuevas a procesar con Groq: {len(new_articles_to_process)} (de {len(articles)} detectadas)")

        new_analyzed = []
        for i in range(0, len(new_articles_to_process), batch_size):
            batch = new_articles_to_process[i:i + batch_size]
            print(f"Procesando lote {i // batch_size + 1} ({len(batch)} noticias)...")
            results = self.analyze_batch(batch)
            new_analyzed.extend(results)

        # Combinar resultados nuevos con caché
        all_items = new_analyzed + cached_items

        # Asignar IDs correlativos
        for i, item in enumerate(all_items):
            item["id"] = i + 1

        if new_analyzed:
            save_news_cache(all_items)
            print(f"Se añadieron {len(new_analyzed)} noticias nuevas al caché.")

        return all_items
