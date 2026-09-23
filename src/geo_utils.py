"""
Utilidades geográficas y diccionario de coordenadas para la República Dominicana.
Garantiza precisión en la localización de incidentes policiales y de seguridad.
"""

import random
import unicodedata

# Coordenadas base de provincias, municipios y sectores clave de RD
DOMINICAN_LOCATIONS = {
    # Distrito Nacional y Gran Santo Domingo
    "distrito nacional": (18.4861, -69.9312),
    "santo domingo": (18.4861, -69.9312),
    "santo domingo este": (18.4884, -69.8571),
    "santo domingo norte": (18.5471, -69.9048),
    "santo domingo oeste": (18.5037, -70.0055),
    "los alcarrizos": (18.5220, -70.0150),
    "villa mella": (18.5478, -69.9045),
    "sabana perdida": (18.5320, -69.8732),
    "herrera": (18.4735, -69.9730),
    "boca chica": (18.4497, -69.6053),
    "pedro brand": (18.5644, -70.0886),
    "capotillo": (18.5031, -69.9015),
    "gualey": (18.5015, -69.8885),
    "cristo rey": (18.5020, -69.9280),
    "villa juana": (18.4900, -69.9070),
    "los mina": (18.4960, -69.8650),
    "invivienda": (18.5030, -69.8160),
    "san isidro": (18.5140, -69.7740),
    "la victoria": (18.5830, -69.8240),
    "guachupita": (18.4940, -69.8820),
    
    # Región Cibao / Norte
    "santiago": (19.4517, -70.6970),
    "santiago de los caballeros": (19.4517, -70.6970),
    "cienfuegos": (19.4720, -70.7350),
    "tamboril": (19.4860, -70.6110),
    "navarrete": (19.5590, -70.8710),
    "villa gonzalez": (19.5390, -70.7890),
    "la vega": (19.2220, -70.5296),
    "jarabacoa": (19.1214, -70.6406),
    "constanza": (18.9090, -70.7449),
    "puerto plata": (19.7934, -70.6884),
    "sosua": (19.7523, -70.5204),
    "cabarete": (19.7498, -70.4078),
    "san francisco de macoris": (19.3009, -70.2526),
    "duarte": (19.3009, -70.2526),
    "espallat": (19.3935, -70.5255),
    "moca": (19.3935, -70.5255),
    "bonao": (18.9483, -70.4092),
    "monsenor nouel": (18.9483, -70.4092),
    "cotui": (19.0527, -70.1494),
    "sanchez ramirez": (19.0527, -70.1494),
    "salcedo": (19.3783, -70.4178),
    "hermanas mirabal": (19.3783, -70.4178),
    "tenares": (19.3740, -70.3520),
    "mao": (19.5520, -71.0782),
    "valverde": (19.5520, -71.0782),
    "esperanza": (19.5850, -70.9840),
    "montecristi": (19.8486, -71.6459),
    "dajabon": (19.5488, -71.7083),
    "nagua": (19.3832, -69.8474),
    "maria trinidad sanchez": (19.3832, -69.8474),
    "samana": (19.2056, -69.3369),
    "las terrenas": (19.3214, -69.5372),
    "santiago rodriguez": (19.4800, -71.3400),
    
    # Región Sur
    "san cristobal": (18.4167, -70.1064),
    "haina": (18.4180, -70.0330),
    "bajos de haina": (18.4180, -70.0330),
    "nigua": (18.3840, -70.0520),
    "cambita": (18.4550, -70.2010),
    "bani": (18.2796, -70.3319),
    "peravia": (18.2796, -70.3319),
    "azua": (18.4532, -70.7349),
    "barahona": (18.2085, -71.1008),
    "san juan": (18.8059, -71.2299),
    "san juan de la maguana": (18.8059, -71.2299),
    "elias pina": (18.8789, -71.7031),
    "comendador": (18.8789, -71.7031),
    "bahoruco": (18.4814, -71.4194),
    "neyba": (18.4814, -71.4194),
    "independencia": (18.4917, -71.8503),
    "jimani": (18.4917, -71.8503),
    "pedernales": (18.0384, -71.7440),
    "san jose de ocoa": (18.5466, -70.5063),
    
    # Región Este
    "san pedro de macoris": (18.4539, -69.3086),
    "la romana": (18.4273, -68.9728),
    "higuey": (18.6150, -68.7079),
    "la altagracia": (18.6150, -68.7079),
    "punta cana": (18.5601, -68.3725),
    "bavaro": (18.6819, -68.4447),
    "veron": (18.5980, -68.4680),
    "el seibo": (18.7656, -69.0389),
    "hato mayor": (18.7628, -69.2568),
    "monte plata": (18.8070, -69.7839),
    "bayaguana": (18.7560, -69.6380),
    "yamasa": (18.7730, -69.9570),
}

# Límites geográficos de la República Dominicana
DR_LAT_MIN, DR_LAT_MAX = 17.5, 20.0
DR_LON_MIN, DR_LON_MAX = -72.0, -68.3
DEFAULT_DR_COORDS = (18.4861, -69.9312)  # Santo Domingo (DN)


def normalize_text(text: str) -> str:
    """Normaliza texto eliminando tildes y caracteres especiales para matching."""
    if not text:
        return ""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def geocode_dominican_location(location_name: str, suggested_lat: float = None, suggested_lon: float = None) -> tuple[float, float]:
    """
    Determina las coordenadas óptimas dentro del territorio de la República Dominicana.
    1. Si se proveen coordenadas sugeridas válidas dentro de los límites de RD, las usa.
    2. Si no, busca en el diccionario local de sectores/municipios dominicanos.
    3. Si todo falla, usa Santo Domingo como punto central de referencia.
    """
    # 1. Verificar si las sugeridas son válidas
    if suggested_lat is not None and suggested_lon is not None:
        # Corregir signos comunes de LLM
        lat = abs(float(suggested_lat))
        lon = -abs(float(suggested_lon))
        if DR_LAT_MIN <= lat <= DR_LAT_MAX and DR_LON_MIN <= lon <= DR_LON_MAX:
            return lat, lon

    # 2. Buscar por nombre de ubicación
    norm_loc = normalize_text(location_name)
    if norm_loc:
        # Match exacto o por contención
        for place, coords in DOMINICAN_LOCATIONS.items():
            if place in norm_loc or norm_loc in place:
                return coords

    # 3. Fallback a Santo Domingo
    return DEFAULT_DR_COORDS


def apply_jitter(lat: float, lon: float, amount: float = 0.008) -> tuple[float, float]:
    """
    Aplica una ligera dispersión pseudoaleatoria para que múltiples
    marcadores en una misma ciudad/sector no queden totalmente encimados.
    """
    j_lat = lat + random.uniform(-amount, amount)
    j_lon = lon + random.uniform(-amount, amount)
    
    # Asegurar que se mantenga dentro de los límites
    j_lat = max(DR_LAT_MIN, min(DR_LAT_MAX, j_lat))
    j_lon = max(DR_LON_MIN, min(DR_LON_MAX, j_lon))
    return round(j_lat, 5), round(j_lon, 5)
