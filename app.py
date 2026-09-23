"""
================================================================================
SISTEMA DE MONITOREO DE SEGURIDAD, DICRIM Y POLICIA NACIONAL (REPUBLICA DOMINICANA)
================================================================================
Dashboard interactivo en Streamlit optimizado para despliegue público y Vercel:
- Persistencia en base de datos SQLite.
- Consulta de incidentes y cards en 1 solo request.
- Contadores y datos en caché con actualización automática cada 15 minutos (TTL = 900s).
- Monitor en segundo plano revisando noticias cada 5 minutos (solo llama a Groq si hay titulares nuevos).
- Sin botones manuales de actualización para usuarios finales.
- Sin emojis.
"""

import streamlit as st
import pandas as pd
import altair as alt
from streamlit_folium import st_folium
import os
import json
from datetime import datetime
from pathlib import Path
import importlib

import src.map_builder as mb
importlib.reload(mb)
from src.map_builder import build_dominican_map
from src.database import get_dashboard_payload_single_request
from src.background_monitor import start_background_monitor, get_monitor_status

# Iniciar monitor de fondo (revisa noticias cada 5 minutos de forma autónoma)
start_background_monitor(interval_seconds=300)

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Sistema de Monitoreo Policial RD | DICRIM & PN",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS tácticos y sobrios (sin emojis)
st.markdown("""
<style>
    /* Contenedor de métricas */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .metric-val {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 4px 0;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 2px;
    }

    /* Alerta informativa destacada */
    .in-map-alert {
        background: rgba(30, 41, 59, 0.85);
        border-left: 4px solid #38bdf8;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 16px;
        color: #e2e8f0;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# CARGA DE DATOS EN 1 SOLO REQUEST CON CACHE DE 15 MINUTOS (TTL = 900s)
# ==============================================================================
@st.cache_data(ttl=900)
def load_dashboard_data_cached():
    """
    Obtiene todos los incidentes y métricas desde SQLite en un solo request.
    Se mantiene en caché durante 15 minutos sin recalcular a cada rato.
    """
    return get_dashboard_payload_single_request()


dashboard_data = load_dashboard_data_cached()
all_incidents = dashboard_data.get("incidents", [])
last_updated_at = dashboard_data.get("updated_at", "")


# ==============================================================================
# BARRA LATERAL: FILTROS Y ESTADO DEL SISTEMA (SIN BOTONES MANUALES)
# ==============================================================================
with st.sidebar:
    st.markdown("### Radar Táctico RD")
    st.markdown("**Monitoreo DICRIM / Policía Nacional / Bandas**")
    st.markdown("---")

    st.markdown("#### Filtros de Búsqueda")

    # 1. Filtro por Categoría
    all_categories = sorted(list({item.get("categoria", "OTRO") for item in all_incidents}))
    selected_category = st.selectbox(
        "Categoría de Hecho:",
        options=["TODAS"] + all_categories,
        index=0
    )

    # 2. Filtro por Tipo de Resultado / Métricas
    outcome_filter = st.selectbox(
        "Filtro por Desenlace:",
        options=[
            "Todos los Incidentes",
            "Con Arrestados (> 0)",
            "Con Abatidos (> 0)",
            "Con Entregados (> 0)"
        ],
        index=0
    )

    # 3. Filtro por Ubicación / Provincia
    all_locations = sorted(list({item.get("ubicacion", "RD") for item in all_incidents}))
    selected_location = st.selectbox(
        "Provincia / Sector:",
        options=["Todas las Ubicaciones"] + all_locations,
        index=0
    )

    # 4. Buscador por texto
    search_query = st.text_input("Buscar palabras clave:", placeholder="Ej: Santiago, drogas, prófugo...")

    # 5. Opciones del Mapa
    st.markdown("---")
    st.markdown("#### Opciones de Visualización")
    use_clustering = st.checkbox("Agrupar marcadores (Clustering)", value=False, help="Agrupa puntos cercanos cuando hay múltiples incidentes en una misma provincia.")

    # Información de actualización automática (sin botón manual)
    st.markdown("---")
    st.markdown("#### Estado de Actualización")
    st.caption("Actualización de contadores: **Automática cada 15 min**")
    st.caption("Revisión de noticias: **Cada 5 min (en segundo plano)**")
    st.caption(f"Registros en SQLite: **{len(all_incidents)}** incidentes")
    st.caption("Motor IA: **Groq (openai/gpt-oss-120b)**")
    st.caption(f"Última lectura en memoria: {last_updated_at}")


# ==============================================================================
# APLICAR FILTROS SOBRE EL DATASET
# ==============================================================================
filtered_news = all_incidents.copy()

if selected_category != "TODAS":
    filtered_news = [it for it in filtered_news if it.get("categoria") == selected_category]

if outcome_filter == "Con Arrestados (> 0)":
    filtered_news = [it for it in filtered_news if it.get("arrestados", 0) > 0]
elif outcome_filter == "Con Abatidos (> 0)":
    filtered_news = [it for it in filtered_news if it.get("abatidos", 0) > 0]
elif outcome_filter == "Con Entregados (> 0)":
    filtered_news = [it for it in filtered_news if it.get("entregados", 0) > 0]

if selected_location != "Todas las Ubicaciones":
    filtered_news = [it for it in filtered_news if it.get("ubicacion") == selected_location]

if search_query:
    q = search_query.lower().strip()
    filtered_news = [
        it for it in filtered_news
        if q in it.get("title", "").lower()
        or q in it.get("summary", "").lower()
        or q in it.get("ubicacion", "").lower()
    ]


# ==============================================================================
# ENCABEZADO PRINCIPAL
# ==============================================================================
st.markdown("<h1 style='margin-bottom: 0px;'>Sistema de Monitoreo Policial y Seguridad RD</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.05rem; margin-top: 4px;'>Filtrado e inteligencia de noticias de República Dominicana: <b>DICRIM</b>, <b>Policía Nacional</b>, <b>bandas criminales</b> y <b>operativos</b>.</p>", unsafe_allow_html=True)

# ==============================================================================
# CONTADORES KPI (ACTUALIZADOS CADA 15 MIN EN CACHÉ)
# ==============================================================================
total_arrestados = sum(it.get("arrestados", 0) for it in filtered_news)
total_abatidos = sum(it.get("abatidos", 0) for it in filtered_news)
total_entregados = sum(it.get("entregados", 0) for it in filtered_news)
total_incidentes = len(filtered_news)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #38bdf8;">
        <div class="metric-label">Total Arrestados</div>
        <div class="metric-val" style="color: #38bdf8;">{total_arrestados}</div>
        <div class="metric-sub">Detenidos por autoridades</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #f87171;">
        <div class="metric-label">Total Abatidos</div>
        <div class="metric-val" style="color: #f87171;">{total_abatidos}</div>
        <div class="metric-sub">Fallecidos en enfrentamientos</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #4ade80;">
        <div class="metric-label">Total Entregados</div>
        <div class="metric-val" style="color: #4ade80;">{total_entregados}</div>
        <div class="metric-sub">Prófugos entregados a la justicia</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #a855f7;">
        <div class="metric-label">Incidentes Filtrados</div>
        <div class="metric-val" style="color: #c084fc;">{total_incidentes}</div>
        <div class="metric-sub">Casos de seguridad clasificados</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# MAPA INTERACTIVO CON CARDS INTEGRADAS DENTRO DEL MAPA
# ==============================================================================
st.markdown("""
<div class="in-map-alert">
    <b>MAPA INTERACTIVO DE HECHOS POLICIALES EN REPUBLICA DOMINICANA:</b><br>
    Las tarjetas (cards) informativas con el detalle de la noticia se encuentran <b>incorporadas 100% dentro del mapa</b>:
    <ul style="margin-top: 6px; margin-bottom: 2px;">
        <li><b>Popup Cards en Marcadores:</b> Haz clic en cualquier pin del mapa para abrir la tarjeta emergente completa de la noticia.</li>
        <li><b>In-Map HUD / Visor Flotante:</b> En la esquina superior derecha <i>dentro del marco del mapa</i>, dispones del panel interactivo con las tarjetas de todos los incidentes mapeados. Haz clic en cualquiera de ellas para centrar el mapa en la ubicación del hecho.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Construir el mapa interactivo con Folium
folium_map = build_dominican_map(filtered_news, use_cluster=use_clustering)

# Renderizar el mapa ocupando el ancho completo y 720px de alto
map_data = st_folium(
    folium_map,
    width="100%",
    height=720,
    returned_objects=[]
)


# ==============================================================================
# PESTAÑAS INFERIORES: DETALLE, ANALÍTICA Y ESTADO
# ==============================================================================
tab_cards, tab_stats, tab_info = st.tabs([
    "Fichas y Registro Detallado",
    "Estadísticas y Georadar",
    "Estado y Fuentes del Sistema"
])

# ------------------------------------------------------------------------------
# TAB 1: Registro detallado y tabla de datos
# ------------------------------------------------------------------------------
with tab_cards:
    st.markdown("### Registro Completo de Noticias de Seguridad")
    
    if filtered_news:
        table_rows = []
        for it in filtered_news:
            table_rows.append({
                "ID": it.get("id"),
                "Fecha": it.get("published"),
                "Categoría": it.get("categoria"),
                "Ubicación": it.get("ubicacion"),
                "Arrestados": it.get("arrestados", 0),
                "Abatidos": it.get("abatidos", 0),
                "Entregados": it.get("entregados", 0),
                "Titular": it.get("title"),
                "Medio": it.get("source"),
                "Enlace": it.get("link")
            })

        df = pd.DataFrame(table_rows)

        st.dataframe(
            df,
            column_config={
                "Enlace": st.column_config.LinkColumn("Leer Noticia", display_text="Abrir ->")
            },
            width="stretch",
            hide_index=True
        )

        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Reporte en CSV",
            data=csv_data,
            file_name=f"reporte_seguridad_rd_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No hay noticias que coincidan con los filtros seleccionados.")

# ------------------------------------------------------------------------------
# TAB 2: Estadísticas y Analítica
# ------------------------------------------------------------------------------
with tab_stats:
    st.markdown("### Georadar y Desglose Estadístico")
    
    if filtered_news:
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Distribución de Incidentes por Ubicación")
            loc_counts = pd.Series([it.get("ubicacion", "Sin especificar") for it in filtered_news]).value_counts().reset_index()
            loc_counts.columns = ["Ubicación", "Incidentes"]
            
            bar_chart = alt.Chart(loc_counts.head(10)).mark_bar(color="#38bdf8", cornerRadiusEnd=4).encode(
                x=alt.X("Incidentes:Q", title="Cantidad de Noticias"),
                y=alt.Y("Ubicación:N", sort="-x", title="Sector / Provincia"),
                tooltip=["Ubicación", "Incidentes"]
            ).properties(height=320)
            
            st.altair_chart(bar_chart, width="stretch")

        with col_chart2:
            st.markdown("#### Proporción de Resultados de Autoridades")
            totals_df = pd.DataFrame({
                "Resultado": ["Arrestados", "Abatidos", "Entregados"],
                "Total": [total_arrestados, total_abatidos, total_entregados]
            })
            
            outcome_chart = alt.Chart(totals_df).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("Total:Q", title="Personas"),
                y=alt.Y("Resultado:N", sort=None, title=""),
                color=alt.Color("Resultado:N", scale=alt.Scale(
                    domain=["Arrestados", "Abatidos", "Entregados"],
                    range=["#38bdf8", "#f87171", "#4ade80"]
                ), legend=None),
                tooltip=["Resultado", "Total"]
            ).properties(height=320)
            
            st.altair_chart(outcome_chart, width="stretch")

        # Gráfico por Categoría
        st.markdown("#### Distribución por Categoría de Seguridad")
        cat_counts = pd.Series([it.get("categoria", "OTRO") for it in filtered_news]).value_counts().reset_index()
        cat_counts.columns = ["Categoría", "Casos"]
        
        cat_chart = alt.Chart(cat_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Casos", type="quantitative"),
            color=alt.Color(field="Categoría", type="nominal", scale=alt.Scale(scheme="category10")),
            tooltip=["Categoría", "Casos"]
        ).properties(height=280)
        
        st.altair_chart(cat_chart, width="stretch")

    else:
        st.info("Sin datos para generar estadísticas con los filtros actuales.")

# ------------------------------------------------------------------------------
# TAB 3: Información y Fuentes
# ------------------------------------------------------------------------------
with tab_info:
    st.markdown("### Fuentes y Criterios de Monitoreo")
    
    status = get_monitor_status()
    st.markdown(f"""
    #### Estado del Monitor en Segundo Plano
    - **Revisión de Noticias**: Cada 5 minutos (300 segundos).
    - **Llamadas a Groq**: Únicamente cuando aparecen titulares que no existen en SQLite.
    - **Total de Revisiones Realizadas**: `{status.get('total_checks', 0)}`
    - **Última Verificación**: `{status.get('last_check', 'Iniciando...')}`
    - **Últimos Incidentes Agregados**: `{status.get('last_new_count', 0)}`
    
    #### Arquitectura de Despliegue en Vercel
    - **Base de Datos**: SQLite (`news_database.db`), trayendo todos los incidentes y cards en **1 solo request SQL**.
    - **Caché CDN / Edge**: 15 minutos (`s-maxage=900`) para garantizar alta velocidad con 0 sobrecarga.
    - **Vercel Cron**: Tarea programada en `vercel.json` (`*/5 * * * *`) apuntando a `/api/cron`.
    - **Endpoint API**: `/api/incidents` para consumo web.
    """)
