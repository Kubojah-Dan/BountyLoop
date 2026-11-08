import React from 'react';
import { Activity, ShieldCheck, Wifi } from 'lucide-react';

interface NavbarProps {
  isLive?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ isLive = true }) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <div className="h-9 w-9 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-lg shadow-sm">
          BL
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-900 tracking-tight text-lg">BountyLoop</span>
            <span className="px-2 py-0.5 text-xs font-semibold bg-brand-100 text-brand-800 rounded-full">
              Operations Hub
            </span>
          </div>
          <p className="text-xs text-slate-500">Autonomous Food Rescue & Multi-Agent Routing</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
          <Wifi className={`w-3.5 h-3.5 ${isLive ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
          <span>{isLive ? 'Live WebSocket Active' : 'Polling Mode'}</span>
        </div>

        <div className="flex items-center space-x-2 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Activity className="w-3.5 h-3.5 text-emerald-600" />
          <span>AI Cascade Operational</span>
        </div>

        <div className="flex items-center space-x-1.5 text-xs text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1 rounded-md">
          <ShieldCheck className="w-4 h-4 text-brand-600" />
          <span className="font-semibold">Operator / Admin</span>
        </div>
      </div>
    </header>
  );
};

