import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Radio,
  ClipboardList,
  Map,
  BarChart3,
  Building2,
  Settings,
  Sparkles,
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Live Rescue Feed', icon: Radio, badge: 'Live' },
  { path: '/review-queue', label: 'Human Review Queue', icon: ClipboardList, badgeAlert: true },
  { path: '/map', label: 'Active Map & Routes', icon: Map },
  { path: '/impact', label: 'Impact Analytics', icon: BarChart3 },
  { path: '/recipients', label: 'Shelters & Food Banks', icon: Building2 },
  { path: '/settings', label: 'System Settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center space-x-2 text-xs font-semibold text-brand-300 uppercase tracking-wider mb-1">
          <Sparkles className="w-3.5 h-3.5 text-brand-400" />
          <span>Dispatch & Control</span>
        </div>
        <p className="text-xs text-slate-400">Austin Metropolitan Area (Zone TX-01)</p>
      </div>

      <nav className="p-3 space-y-1 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400">
        <div className="flex justify-between items-center mb-1">
          <span>Release Tier</span>
          <span className="font-mono text-emerald-400">v0.1.0-prod</span>
        </div>
        <div className="flex justify-between items-center">
          <span>Target Platform</span>
          <span className="text-slate-300">Render + Neon + Vercel</span>
        </div>
      </div>
    </aside>
  );
};

