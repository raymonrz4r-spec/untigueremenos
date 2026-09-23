"""
Generador de mapa interactivo con Folium para República Dominicana.
Implementa tarjetas (cards) informativas 100% VISUALIZADAS DENTRO DEL MAPA:
1. Popup Cards enriquecidas en cada marcador (sin emojis).
2. In-Map HUD flotante interactivo con cards limpias y sobrias.
"""

import folium
from folium import plugins
import html


def get_category_color(category: str, abatidos: int = 0, arrestados: int = 0, entregados: int = 0) -> dict:
    """Devuelve la paleta de colores según el tipo de incidente."""
    cat = (category or "").upper()
    if abatidos > 0:
        return {"folium": "red", "bg": "#dc2626", "badge": "bg-red-600", "label": "ABATIDO / ENFRENTAMIENTO", "icon": "remove"}
    elif entregados > 0 and arrestados == 0:
        return {"folium": "green", "bg": "#16a34a", "badge": "bg-green-600", "label": "ENTREGADO", "icon": "ok"}
    elif "DICRIM" in cat:
        return {"folium": "darkblue", "bg": "#1d4ed8", "badge": "bg-blue-700", "label": "DICRIM", "icon": "bookmark"}
    elif "BANDA" in cat:
        return {"folium": "purple", "bg": "#7e22ce", "badge": "bg-purple-700", "label": "BANDA CRIMINAL", "icon": "flag"}
    elif "OPERATIVO" in cat:
        return {"folium": "orange", "bg": "#ea580c", "badge": "bg-orange-600", "label": "OPERATIVO POLICIAL", "icon": "briefcase"}
    else:
        return {"folium": "blue", "bg": "#2563eb", "badge": "bg-blue-600", "label": "POLICIA NACIONAL", "icon": "info-sign"}


def create_popup_card_html(item: dict) -> str:
    """Genera la card HTML moderna que se despliega directamente sobre el marcador dentro del mapa."""
    color_info = get_category_color(
        item.get("categoria", ""),
        item.get("abatidos", 0),
        item.get("arrestados", 0),
        item.get("entregados", 0)
    )

    title = html.escape(item.get("title", "Incidente Reportado"))
    summary = html.escape(item.get("summary", "Sin descripción detallada."))
    location = html.escape(item.get("ubicacion", "República Dominicana"))
    source = html.escape(item.get("source", "Medio Dominicano"))
    published = html.escape(item.get("published", ""))
    link = item.get("link", "#")

    arrestados = item.get("arrestados", 0)
    abatidos = item.get("abatidos", 0)
    entregados = item.get("entregados", 0)

    card_content = f"""
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        width: 295px;
        box-sizing: border-box;
        padding: 12px;
        background: #ffffff;
        border-radius: 10px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.22);
        border: 1px solid #e2e8f0;
    ">
        <!-- Encabezado con Categoría y Ubicación -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="
                background: {color_info['bg']};
                color: #ffffff;
                font-size: 10px;
                font-weight: 800;
                padding: 3px 8px;
                border-radius: 4px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            ">
                {color_info['label']}
            </span>
            <span style="font-size: 11px; font-weight: 700; color: #475569;">
                {location}
            </span>
        </div>

        <!-- Titular de la Noticia -->
        <h4 style="
            margin: 0 0 6px 0;
            font-size: 13px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.35;
        ">
            {title}
        </h4>

        <!-- Resumen del Hecho -->
        <p style="
            margin: 0 0 10px 0;
            font-size: 11.5px;
            color: #334155;
            line-height: 1.45;
            background: #f8fafc;
            padding: 8px;
            border-radius: 6px;
            border-left: 3px solid {color_info['bg']};
        ">
            {summary}
        </p>

        <!-- Métricas Clave Requeridas (Arrestados, Abatidos, Entregados) -->
        <div style="
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 4px;
            background: #0f172a;
            padding: 6px 4px;
            border-radius: 6px;
            margin-bottom: 10px;
            text-align: center;
        ">
            <div>
                <div style="font-size: 14px; font-weight: 800; color: #38bdf8;">{arrestados}</div>
                <div style="font-size: 9px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Arrestados</div>
            </div>
            <div>
                <div style="font-size: 14px; font-weight: 800; color: #f87171;">{abatidos}</div>
                <div style="font-size: 9px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Abatidos</div>
            </div>
            <div>
                <div style="font-size: 14px; font-weight: 800; color: #4ade80;">{entregados}</div>
                <div style="font-size: 9px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Entregados</div>
            </div>
        </div>

        <!-- Pie con Fuente y Enlace a Noticia Completa -->
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 8px;">
            <div style="font-size: 10px; color: #64748b;">
                Fuente: {source}<br>
                <span style="font-size: 9px; color: #94a3b8;">{published}</span>
            </div>
            <a href="{link}" target="_blank" rel="noopener noreferrer" style="
                display: inline-block;
                background: #1e293b;
                color: #ffffff;
                text-decoration: none;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 4px;
            ">
                Leer Noticia &rarr;
            </a>
        </div>
    </div>
    """
    return card_content


def build_dominican_map(news_items: list[dict], use_cluster: bool = False) -> folium.Map:
    """
    Construye el mapa Folium centrado en República Dominicana.
    Integra marcadores con popup cards y un HUD flotante interactivo IN-MAP.
    """
    center_lat, center_lon = 18.7357, -70.1627
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True
    )

    # Añadir capa de pantalla completa
    plugins.Fullscreen(
        position="topleft",
        title="Pantalla Completa",
        title_cancel="Salir de Pantalla Completa",
        force_separate_button=True
    ).add_to(m)

    # Contenedor para marcadores
    if use_cluster:
        marker_group = plugins.MarkerCluster(name="Agrupacion de Incidentes").add_to(m)
    else:
        marker_group = folium.FeatureGroup(name="Noticias de Seguridad RD").add_to(m)

    total_arrestados = sum(it.get("arrestados", 0) for it in news_items)
    total_abatidos = sum(it.get("abatidos", 0) for it in news_items)
    total_entregados = sum(it.get("entregados", 0) for it in news_items)

    # Agregar cada marcador al mapa
    for idx, item in enumerate(news_items):
        lat = item.get("lat")
        lon = item.get("lon")
        if not lat or not lon:
            continue

        color_info = get_category_color(
            item.get("categoria", ""),
            item.get("abatidos", 0),
            item.get("arrestados", 0),
            item.get("entregados", 0)
        )

        card_html = create_popup_card_html(item)
        iframe = folium.IFrame(card_html, width=315, height=275)
        popup = folium.Popup(iframe, max_width=330)

        tooltip_text = (
            f"<b>{item.get('categoria', 'INCIDENTE')}</b>: {item.get('title', '')[:50]}...<br>"
            f"{item.get('ubicacion', 'RD')} | Arrestados: {item.get('arrestados', 0)} | Abatidos: {item.get('abatidos', 0)} | Entregados: {item.get('entregados', 0)}<br>"
            f"<i>Clic para abrir reporte en mapa</i>"
        )

        marker = folium.Marker(
            location=[lat, lon],
            popup=popup,
            tooltip=tooltip_text,
            icon=folium.Icon(
                color=color_info["folium"],
                icon=color_info["icon"],
                prefix="glyphicon"
            )
        )
        marker.add_to(marker_group)

    # Renderizar DIRECTAMENTE en Python las cards dentro del HUD
    rendered_cards = []
    for it in news_items:
        c_title = html.escape(it.get("title", ""))
        c_summary = html.escape(it.get("summary", ""))
        c_loc = html.escape(it.get("ubicacion", "RD"))
        c_cat = html.escape(it.get("categoria", "POLICIA_NACIONAL"))
        c_link = it.get("link", "#")
        c_arr = it.get("arrestados", 0)
        c_abat = it.get("abatidos", 0)
        c_entr = it.get("entregados", 0)
        c_lat = it.get("lat", 18.7357)
        c_lon = it.get("lon", -70.1627)

        border_c = "#ef4444" if c_abat > 0 else ("#38bdf8" if c_arr > 0 else ("#4ade80" if c_entr > 0 else "#818cf8"))

        card_snippet = f"""
        <div class="hud-card-item" style="border-left: 4px solid {border_c};" onclick="panMapTo({c_lat}, {c_lon});">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 9.5px; font-weight: 700; color: {border_c}; text-transform: uppercase;">{c_cat}</span>
                <span style="font-size: 10px; color: #94a3b8; font-weight: 500;">{c_loc}</span>
            </div>
            <div style="font-size: 11.5px; font-weight: 600; color: #f1f5f9; line-height: 1.3; margin-bottom: 5px;">
                {c_title}
            </div>
            <div style="font-size: 10.5px; color: #cbd5e1; line-height: 1.35; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                {c_summary}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.6); padding: 4px 6px; border-radius: 6px;">
                <div style="display: flex; gap: 8px; font-size: 10px; font-weight: 700;">
                    <span style="color: #38bdf8;">Arr: {c_arr}</span>
                    <span style="color: #f87171;">Abat: {c_abat}</span>
                    <span style="color: #4ade80;">Entr: {c_entr}</span>
                </div>
                <a href="{c_link}" target="_blank" onclick="event.stopPropagation();" style="color: #60a5fa; font-size: 10px; font-weight: 600; text-decoration: none;">Abrir &rarr;</a>
            </div>
        </div>
        """
        rendered_cards.append(card_snippet)

    all_cards_html = "\n".join(rendered_cards) if rendered_cards else '<div style="font-size: 11px; color: #94a3b8; text-align: center; padding: 16px;">No hay incidentes para los filtros actuales.</div>'

    # Inyección directa de HTML + CSS
    hud_element_html = f"""
    <style>
        #hud-body::-webkit-scrollbar {{
            width: 6px;
        }}
        #hud-body::-webkit-scrollbar-track {{
            background: rgba(15, 23, 42, 0.6);
            border-radius: 4px;
        }}
        #hud-body::-webkit-scrollbar-thumb {{
            background: #475569;
            border-radius: 4px;
        }}
        #hud-body::-webkit-scrollbar-thumb:hover {{
            background: #38bdf8;
        }}
        .hud-card-item {{
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 9px 11px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .hud-card-item:hover {{
            background: rgba(51, 65, 85, 0.98) !important;
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.6);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
    </style>

    <div id="in-map-hud-container" style="
        position: absolute !important;
        top: 14px !important;
        right: 14px !important;
        width: 340px !important;
        height: 540px !important;
        max-height: calc(100% - 30px) !important;
        z-index: 1000 !important;
        background: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 35px rgba(0,0,0,0.55) !important;
        color: #f8fafc !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        display: flex !important;
        flex-direction: column !important;
    ">
        <!-- Cabecera del HUD dentro del mapa -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            background: rgba(30, 41, 59, 0.98);
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        ">
            <div>
                <div style="font-size: 12px; font-weight: 800; letter-spacing: 0.5px; color: #38bdf8;">RADAR DICRIM & PN</div>
                <div style="font-size: 9px; color: #94a3b8; font-weight: 600;">REPUBLICA DOMINICANA</div>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="background: #ef4444; color: white; font-size: 9px; font-weight: 800; padding: 2px 7px; border-radius: 4px;">EN VIVO</span>
                <button id="hud-toggle-btn" onclick="
                    const b = document.getElementById('hud-body');
                    const c = document.getElementById('in-map-hud-container');
                    if(b.style.display==='none'){{ b.style.display='block'; c.style.height='540px'; this.innerText='[-]'; }}
                    else {{ b.style.display='none'; c.style.height='44px'; this.innerText='[+]'; }}
                " style="
                    background: #334155;
                    border: none;
                    color: #e2e8f0;
                    cursor: pointer;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 7px;
                    border-radius: 4px;
                " title="Minimizar / Expandir panel">[-]</button>
            </div>
        </div>

        <!-- Cuerpo del HUD (desplegable) -->
        <div id="hud-body" style="padding: 12px; overflow-y: auto; height: calc(100% - 46px); box-sizing: border-box;">
            <!-- Totales en vivo dentro del mapa -->
            <div style="
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 6px;
                background: rgba(30, 41, 59, 0.8);
                padding: 8px 6px;
                border-radius: 8px;
                margin-bottom: 12px;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.08);
            ">
                <div>
                    <div style="font-size: 17px; font-weight: 800; color: #38bdf8;">{total_arrestados}</div>
                    <div style="font-size: 8.5px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Arrestados</div>
                </div>
                <div>
                    <div style="font-size: 17px; font-weight: 800; color: #f87171;">{total_abatidos}</div>
                    <div style="font-size: 8.5px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Abatidos</div>
                </div>
                <div>
                    <div style="font-size: 17px; font-weight: 800; color: #4ade80;">{total_entregados}</div>
                    <div style="font-size: 8.5px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Entregados</div>
                </div>
            </div>

            <!-- Título de sección de cards -->
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
                padding: 0 2px;
            ">
                <span style="font-size: 10.5px; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px;">
                    CARDS DE NOTICIAS ({len(news_items)})
                </span>
                <span style="font-size: 9.5px; color: #94a3b8;">Clic para ubicar</span>
            </div>

            <!-- Lista de cards renderizadas -->
            <div id="hud-news-feed" style="display: flex; flex-direction: column; gap: 8px;">
                {all_cards_html}
            </div>
        </div>
    </div>

    <script>
        function panMapTo(lat, lon) {{
            for (let k in window) {{
                if (k.startsWith('map_') && window[k] && typeof window[k].setView === 'function') {{
                    window[k].setView([lat, lon], 14, {{ animate: true }});
                    window[k].eachLayer(function(l) {{
                        if (l instanceof L.Marker) {{
                            const pos = l.getLatLng();
                            if (Math.abs(pos.lat - lat) < 0.001 && Math.abs(pos.lng - lon) < 0.001) {{
                                l.openPopup();
                            }}
                        }}
                    }});
                    break;
                }}
            }}
        }}
    </script>
    """

    m.get_root().html.add_child(folium.Element(hud_element_html))

    return m
