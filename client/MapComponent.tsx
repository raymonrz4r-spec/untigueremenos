import { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default Leaflet icon issues
// No default import needed

function MapUpdater({ incidents }: { incidents: any[] }) {
  const map = useMap();
  useEffect(() => {
    if (incidents.length > 0) {
      // Optional: Auto-center on incidents
      // map.fitBounds(L.featureGroup(incidents.map(i => L.marker([i.lat, i.lon]))).getBounds());
    }
  }, [incidents, map]);
  return null;
}

export default function MapComponent({ incidents }: { incidents: any[] }) {
  return (
    <div className="w-full h-full min-h-[500px] z-10 relative">
      <MapContainer 
        center={[18.7357, -70.1627]} 
        zoom={8} 
        style={{ height: '100%', width: '100%', background: 'transparent' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          className="map-tiles"
        />
        {incidents.map((item, idx) => {
          const borderC = item.abatidos > 0 ? '#ef4444' : (item.arrestados > 0 ? '#38bdf8' : (item.entregados > 0 ? '#4ade80' : '#818cf8'));
          return (
            <CircleMarker
              key={item.id || idx}
              center={[item.lat, item.lon]}
              radius={8}
              pathOptions={{ fillColor: borderC, color: '#ffffff', weight: 2, fillOpacity: 0.9, opacity: 1 }}
            >
              <Popup>
                <div style={{ width: '260px', fontFamily: 'sans-serif', padding: '2px' }}>
                  <div style={{ fontSize: '10px', fontWeight: 'bold', color: borderC, textTransform: 'uppercase' }}>
                    {item.categoria} | {item.ubicacion}
                  </div>
                  <h4 style={{ fontSize: '13px', margin: '4px 0', color: '#0f172a' }}>{item.title}</h4>
                  <p style={{ fontSize: '11px', color: '#334155', marginBottom: '8px' }}>{item.summary}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', background: '#0f172a', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '10px', marginBottom: '6px' }}>
                    <span>Arr: <b>{item.arrestados}</b></span>
                    <span>Abat: <b>{item.abatidos}</b></span>
                    <span>Entr: <b>{item.entregados}</b></span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <a href={item.link} target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontSize: '11px', fontWeight: 600, textDecoration: 'none' }}>Leer Noticia -{'>'}</a>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
        <MapUpdater incidents={incidents} />
      </MapContainer>
      <style>{`
        .map-tiles {
          filter: brightness(0.6) invert(1) contrast(3) hue-rotate(200deg) saturate(0.3) brightness(0.7);
        }
        .leaflet-container {
          background: #0f172a !important;
        }
      `}</style>
    </div>
  );
}
