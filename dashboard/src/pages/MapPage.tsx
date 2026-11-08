import React, { useState } from 'react';
import { MapPin, Navigation, Compass, Layers, ShieldCheck } from 'lucide-react';

interface MapPoint {
  id: string;
  name: string;
  type: 'donor' | 'recipient' | 'active_offer';
  lat: number;
  lng: number;
  address: string;
  details?: string;
}

const mockPoints: MapPoint[] = [
  { id: '1', name: 'Central Market North', type: 'donor', lat: 30.3065, lng: -97.7408, address: '4001 N Lamar Blvd', details: 'Fresh produce, bakery surplus' },
  { id: '2', name: 'Austin Food Bank Central', type: 'recipient', lat: 30.2038, lng: -97.7471, address: '6500 Metropolis Dr', details: 'Capacity: 1200 kg/day' },
  { id: '3', name: 'Caritas Community Kitchen', type: 'recipient', lat: 30.2701, lng: -97.7402, address: '611 Neches St', details: 'Prepared meals, capacity: 450 kg/day' },
  { id: '4', name: 'Wheatsville Food Co-op', type: 'donor', lat: 30.2974, lng: -97.7423, address: '3101 Guadalupe St', details: 'Dairy & organic fruits' },
  { id: '5', name: 'Active Route: Apples to Caritas', type: 'active_offer', lat: 30.2830, lng: -97.7410, address: 'Transit Corridor (Lamar to Neches)', details: '8.4 km • 14 min ETA via OSRM' },
];

export const MapPage: React.FC = () => {
  const [selectedPoint, setSelectedPoint] = useState<MapPoint>(mockPoints[4]);
  const [activeFilter, setActiveFilter] = useState<'all' | 'donors' | 'recipients' | 'routes'>('all');

  const filteredPoints = mockPoints.filter((pt) => {
    if (activeFilter === 'donors') return pt.type === 'donor';
    if (activeFilter === 'recipients') return pt.type === 'recipient';
    if (activeFilter === 'routes') return pt.type === 'active_offer';
    return true;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Active Map & Logistics</h1>
          <p className="text-sm text-slate-500">
            PostGIS spatial proximity matching & OSRM vehicle routing engine (Austin Zone)
          </p>
        </div>

        <div className="flex items-center gap-2 bg-white p-1 rounded-lg border border-slate-200 text-xs">
          {(['all', 'donors', 'recipients', 'routes'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1.5 rounded-md font-semibold capitalize transition-colors ${
                activeFilter === filter
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Map Visualizer Canvas */}
        <div className="lg:col-span-2 bg-slate-900 rounded-2xl overflow-hidden border border-slate-800 shadow-md relative min-h-[480px] flex flex-col justify-between p-6">
          <div className="flex items-center justify-between z-10">
            <div className="bg-slate-950/80 backdrop-blur border border-slate-700/60 rounded-xl px-4 py-2 text-xs text-slate-200 flex items-center gap-2">
              <Compass className="w-4 h-4 text-emerald-400" />
              <span>Bounding Box: Austin, TX (EPSG:4326 PostGIS)</span>
            </div>

            <div className="bg-slate-950/80 backdrop-blur border border-slate-700/60 rounded-xl px-3 py-1.5 text-xs text-slate-300 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-brand-400" />
              <span>OpenStreetMap Tiles + OSRM</span>
            </div>
          </div>

          {/* SVG Map Representation */}
          <div className="relative my-auto flex items-center justify-center">
            <svg viewBox="0 0 600 320" className="w-full max-w-xl h-auto opacity-80">
              <defs>
                <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#2D5A3D" />
                  <stop offset="100%" stopColor="#D98E32" />
                </linearGradient>
              </defs>
              {/* Grid Lines */}
              <path d="M 50 0 L 50 320 M 150 0 L 150 320 M 250 0 L 250 320 M 350 0 L 350 320 M 450 0 L 450 320 M 550 0 L 550 320" stroke="#1E293B" strokeWidth="1" />
              <path d="M 0 50 L 600 50 M 0 130 L 600 130 M 0 210 L 600 210 M 0 290 L 600 290" stroke="#1E293B" strokeWidth="1" />
              {/* Colorado River representation */}
              <path d="M 20 230 Q 180 190 320 240 T 580 200" fill="none" stroke="#0F3854" strokeWidth="18" opacity="0.6" />
              {/* OSRM Route line */}
              <path d="M 220 70 Q 240 130 320 160 T 360 210" fill="none" stroke="url(#routeGradient)" strokeWidth="4" strokeDasharray="6 4" className="animate-pulse" />

              {/* Pins */}
              <circle cx="220" cy="70" r="8" fill="#5F9F78" stroke="#FFFFFF" strokeWidth="2" />
              <circle cx="360" cy="210" r="8" fill="#D98E32" stroke="#FFFFFF" strokeWidth="2" />
              <circle cx="160" cy="180" r="6" fill="#4A7C59" stroke="#FFFFFF" strokeWidth="1.5" />
              <circle cx="420" cy="90" r="6" fill="#D98E32" stroke="#FFFFFF" strokeWidth="1.5" />
            </svg>
          </div>

          <div className="z-10 bg-slate-950/80 backdrop-blur border border-slate-700/60 rounded-xl p-3 text-xs text-slate-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              <span>Donors (4 Active)</span>
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 ml-2"></span>
              <span>Food Banks (6 Active)</span>
            </div>
            <span className="text-slate-400">Map data © OpenStreetMap contributors</span>
          </div>
        </div>

        {/* Selected Hub / Active Route Card */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-brand-600">
                Selected Point Inspection
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 capitalize">
                {selectedPoint.type.replace('_', ' ')}
              </span>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900">{selectedPoint.name}</h3>
              <p className="text-xs text-slate-500 mt-0.5">{selectedPoint.address}</p>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Coordinates:</span>
                <span className="font-mono font-medium">{selectedPoint.lat.toFixed(4)}, {selectedPoint.lng.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Logistics Status:</span>
                <span className="font-semibold text-emerald-600">Available / Verified</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Details:</span>
                <span className="text-slate-800 font-medium">{selectedPoint.details}</span>
              </div>
            </div>

            <div className="p-3 bg-brand-50 border border-brand-100 rounded-xl text-xs text-brand-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand-600 shrink-0" />
              <span>OR-Tools CVRP capacity-fit verified for vehicle dispatch.</span>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Points of Interest</h4>
            <div className="space-y-2">
              {filteredPoints.map((pt) => (
                <button
                  key={pt.id}
                  onClick={() => setSelectedPoint(pt)}
                  className={`w-full text-left p-3 rounded-xl border transition-all text-xs flex items-center justify-between ${
                    selectedPoint.id === pt.id
                      ? 'border-brand-500 bg-brand-50/50 shadow-sm'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <MapPin className={`w-4 h-4 ${pt.type === 'recipient' ? 'text-amber-600' : 'text-brand-600'}`} />
                    <div>
                      <div className="font-bold text-slate-800">{pt.name}</div>
                      <div className="text-slate-400 text-[11px]">{pt.address}</div>
                    </div>
                  </div>
                  <Navigation className="w-3.5 h-3.5 text-slate-400" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

