import { useEffect, useState, useMemo } from 'react';
import { Shield, Search } from 'lucide-react';
import MapComponent from './MapComponent';

export default function App() {
  const [data, setData] = useState<any>({ incidents: [], kpis: {}, updated_at: '' });
  const [loading, setLoading] = useState(true);

  // Filtros
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [outcome, setOutcome] = useState('all');
  const [province, setProvince] = useState('all');

  useEffect(() => {
    const fetchData = () => {
      fetch('/api/incidents')
        .then(res => res.json())
        .then(json => {
          setData(json);
          setLoading(false);
        })
        .catch(err => {
          console.error('Error fetching data', err);
          setLoading(false);
        });
    };
    
    // Initial fetch
    fetchData();

    // Auto-refresh every 15 minutes
    const interval = setInterval(fetchData, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const allIncidents = data.incidents || [];

  const filteredIncidents = useMemo(() => {
    return allIncidents.filter((it: any) => {
      // Búsqueda de texto
      if (search) {
        const q = search.toLowerCase();
        if (
          !it.title?.toLowerCase().includes(q) &&
          !it.summary?.toLowerCase().includes(q) &&
          !it.ubicacion?.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      
      // Categoría
      if (category !== 'all' && it.categoria !== category) {
        return false;
      }

      // Desenlace
      if (outcome !== 'all') {
        if (outcome === 'arresto' && (!it.arrestados || it.arrestados === 0)) return false;
        if (outcome === 'abatido' && (!it.abatidos || it.abatidos === 0)) return false;
        if (outcome === 'entregado' && (!it.entregados || it.entregados === 0)) return false;
      }

      // Provincia
      if (province !== 'all') {
        // Asumiendo coincidencia exacta para simplificar
        if (it.ubicacion !== province) return false;
      }

      return true;
    });
  }, [allIncidents, search, category, outcome, province]);

  // Recalcular KPIs basados en filtrado local (igual que Streamlit)
  const totalArrestados = filteredIncidents.reduce((sum: number, it: any) => sum + (it.arrestados || 0), 0);
  const totalAbatidos = filteredIncidents.reduce((sum: number, it: any) => sum + (it.abatidos || 0), 0);
  const totalEntregados = filteredIncidents.reduce((sum: number, it: any) => sum + (it.entregados || 0), 0);
  const totalFiltrados = filteredIncidents.length;

  // Extraer categorías únicas y ubicaciones únicas
  const allCategories = useMemo(() => Array.from(new Set(allIncidents.map((i:any) => i.categoria || 'OTRO'))).sort(), [allIncidents]);
  const allLocations = useMemo(() => Array.from(new Set(allIncidents.map((i:any) => i.ubicacion || 'RD'))).sort(), [allIncidents]);

  return (
    <div className="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans antialiased overflow-x-hidden selection:bg-blue-600 selection:text-white">
      {/* TOP HEADER / BARRA SUPERIOR */}
      <header className="w-full bg-slate-900 border-b border-slate-800/90 px-6 py-3.5 flex items-center justify-between sticky top-0 z-50 backdrop-blur-md">
        <div className="flex items-center space-x-4">
          <div className="h-10 w-10 rounded bg-slate-800 border border-slate-700/80 flex items-center justify-center text-blue-500 shadow-inner">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-base font-bold tracking-wider text-slate-50 uppercase font-mono">
                Centro de Operaciones y Monitoreo Policial
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded bg-blue-950 text-blue-400 border border-blue-800/60 font-mono">
                C4I TÁCTICO
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono tracking-tight">
              DIRECCIÓN CENTRAL DE INVESTIGACIÓN (DICRIM) • POLICÍA NACIONAL
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6">
          <div className="hidden md:flex items-center space-x-4 border-l pl-4 border-slate-800 pr-6 text-xs font-mono">
            <div className="flex items-center space-x-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300">ESTADO API: <span className="text-emerald-400 font-semibold">{loading ? 'CARGANDO' : (data.incidents?.length > 0 ? 'ACTIVA' : 'VACÍA')}</span></span>
            </div>
            <div className="text-slate-500">|</div>
            <div className="text-slate-400">
              ÚLTIMA LECTURA: <span className="text-slate-200">{data.updated_at || '-'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* CONTENIDO PRINCIPAL DEL DASHBOARD */}
      <main className="flex-1 w-full p-4 lg:p-6 flex flex-col space-y-5 max-w-[1920px] mx-auto">
        {/* SECCIÓN DE MÉTRICAS (KPIS) */}
        <section className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* KPI 1: Total Arrestados (Azul) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 relative overflow-hidden shadow-sm hover:border-blue-500/40 transition-colors">
            <div className="absolute top-0 left-0 right-0 h-1 bg-blue-500"></div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-blue-400 font-mono">
                  Total Arrestados
                </span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span className="text-3xl font-bold font-mono tracking-tight text-white">
                    {totalArrestados}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">
                  Detenidos por autoridades
                </p>
              </div>
            </div>
          </div>

          {/* KPI 2: Total Abatidos (Rojo) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 relative overflow-hidden shadow-sm hover:border-red-500/40 transition-colors">
            <div className="absolute top-0 left-0 right-0 h-1 bg-red-500"></div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-red-400 font-mono">
                  Total Abatidos
                </span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span className="text-3xl font-bold font-mono tracking-tight text-white">
                    {totalAbatidos}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">
                  Fallecidos en enfrentamientos
                </p>
              </div>
            </div>
          </div>

          {/* KPI 3: Total Entregados (Verde) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 relative overflow-hidden shadow-sm hover:border-emerald-500/40 transition-colors">
            <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500"></div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-emerald-400 font-mono">
                  Total Entregados
                </span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span className="text-3xl font-bold font-mono tracking-tight text-white">
                    {totalEntregados}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">
                  Prófugos entregados a la justicia
                </p>
              </div>
            </div>
          </div>

          {/* KPI 4: Incidentes Filtrados (Morado) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 relative overflow-hidden shadow-sm hover:border-purple-500/40 transition-colors">
            <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500"></div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-purple-400 font-mono">
                  Incidentes Filtrados
                </span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span className="text-3xl font-bold font-mono tracking-tight text-white">
                    {totalFiltrados}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">
                  De un total de: {allIncidents.length}
                </p>
              </div>
            </div>
          </div>

        </section>

        {/* LAYOUT PRINCIPAL: 2 COLUMNAS */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 items-stretch min-h-[640px]">
          
          {/* COLUMNA IZQUIERDA (3/4): MAPA */}
          <div className="lg:col-span-3 bg-slate-900 border border-slate-800/80 rounded-xl relative flex flex-col overflow-hidden shadow-lg">
            
            <div className="h-12 border-b border-slate-800/80 bg-slate-900/90 px-4 flex items-center justify-between z-20">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-300">
                  <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                  <span className="font-semibold uppercase tracking-wider">VISOR CARTOGRÁFICO GEOESPACIAL</span>
                </div>
              </div>
            </div>

            {/* Renderizar Mapa (Leaflet) */}
            <div className="relative flex-1 bg-slate-950 flex items-center justify-center overflow-hidden min-h-[500px]">
              <MapComponent incidents={filteredIncidents} />
            </div>

            <div className="h-8 border-t border-slate-800/80 bg-slate-900 px-4 flex items-center justify-between text-[11px] font-mono text-slate-400">
              <div>FUENTE: SISTEMA DE INFORMACIÓN GEOGRÁFICA POLICIAL (SIG-PN)</div>
            </div>
          </div>

          {/* COLUMNA DERECHA (1/4): BARRA LATERAL */}
          <aside className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl flex flex-col overflow-hidden shadow-lg h-[640px]">
            <div className="p-4 border-b border-slate-800 bg-slate-850/80">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-blue-500"></span>
                  <h2 className="text-sm font-bold tracking-wider uppercase text-white font-mono">
                    RADAR DICRIM & PN
                  </h2>
                </div>
              </div>

              {/* BÚSQUEDA Y FILTROS */}
              <div className="mt-3.5 space-y-2.5">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Search className="w-3.5 h-3.5" />
                  </div>
                  <input 
                    type="text" 
                    placeholder="Buscar por palabra clave..." 
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono transition"
                  />
                </div>

                <div className="grid grid-cols-1 gap-2">
                  <div>
                    <label className="block text-[10px] uppercase font-mono font-medium text-slate-400 mb-0.5">Categoría</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} className="w-full px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded text-slate-200 font-mono focus:outline-none focus:border-blue-500 cursor-pointer">
                      <option value="all">Todas las Categorías</option>
                      {(allCategories as string[]).map((c: string) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-mono font-medium text-slate-400 mb-0.5">Desenlace</label>
                    <select value={outcome} onChange={e => setOutcome(e.target.value)} className="w-full px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded text-slate-200 font-mono focus:outline-none focus:border-blue-500 cursor-pointer">
                      <option value="all">Todos los Desenlaces</option>
                      <option value="arresto">Con Arrestados ({'>'} 0)</option>
                      <option value="abatido">Con Abatidos ({'>'} 0)</option>
                      <option value="entregado">Con Entregados ({'>'} 0)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-mono font-medium text-slate-400 mb-0.5">Provincia / Ubicación</label>
                    <select value={province} onChange={e => setProvince(e.target.value)} className="w-full px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded text-slate-200 font-mono focus:outline-none focus:border-blue-500 cursor-pointer">
                      <option value="all">Todas las Ubicaciones</option>
                      {(allLocations as string[]).map((l: string) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </div>
                </div>

                <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-slate-400">
                  <span>Filtro: <strong className="text-slate-300">{totalFiltrados} resultados</strong></span>
                  <button onClick={() => { setSearch(''); setCategory('all'); setOutcome('all'); setProvince('all'); }} className="text-blue-400 hover:text-blue-300 underline cursor-pointer">Restablecer</button>
                </div>
              </div>
            </div>

            {/* LISTA DESPLAZABLE */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
              {filteredIncidents.map((item: any) => {
                const isAbatido = item.abatidos > 0;
                const isArrestado = item.arrestados > 0;
                const isEntregado = item.entregados > 0;
                let colorClass = 'border-slate-800 hover:border-slate-500';
                let tagColor = 'bg-slate-900 text-slate-400 border-slate-800';
                let typeStr = 'POLICIA';
                
                if (isAbatido) { colorClass = 'hover:border-red-500/50'; tagColor = 'bg-red-950/80 text-red-400 border-red-800/60'; typeStr = 'ABATIDO'; }
                else if (isArrestado) { colorClass = 'hover:border-blue-500/50'; tagColor = 'bg-blue-950/80 text-blue-400 border-blue-800/60'; typeStr = 'ARRESTADO'; }
                else if (isEntregado) { colorClass = 'hover:border-emerald-500/50'; tagColor = 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'; typeStr = 'ENTREGADO'; }

                return (
                  <article key={item.id} className={`bg-slate-950 border rounded p-3 transition cursor-pointer group ${colorClass}`}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`px-1.5 py-0.5 text-[9px] font-mono font-semibold uppercase rounded border ${tagColor}`}>
                        {item.categoria}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{item.published?.slice(11,16) || ''}</span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 flex items-center space-x-1 mb-1">
                      <span>{item.ubicacion}</span>
                      <span className="text-slate-600">•</span>
                      <span className={isAbatido ? "text-red-400 font-semibold" : (isArrestado ? "text-blue-400 font-semibold" : (isEntregado ? "text-emerald-400 font-semibold" : "text-slate-400 font-semibold"))}>
                        {typeStr}
                      </span>
                    </div>
                    <h3 className="text-xs font-semibold text-slate-100 group-hover:text-white transition leading-snug">
                      {item.title}
                    </h3>
                    <div className="mt-2 pt-2 border-t border-slate-900 flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>Arr: {item.arrestados} | Abat: {item.abatidos} | Entr: {item.entregados}</span>
                      <a href={item.link} target="_blank" rel="noreferrer" className="text-blue-400 font-medium hover:underline">LEER →</a>
                    </div>
                  </article>
                );
              })}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
