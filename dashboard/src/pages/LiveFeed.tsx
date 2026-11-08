import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Donation } from '../types';
import { StatusBadge, FreshnessBadge, HazardBadge } from '../components/StatusBadge';
import { RefreshCw, Package, Clock, User, AlertCircle } from 'lucide-react';

export const LiveFeed: React.FC = () => {
  const [liveDonations, setLiveDonations] = useState<Donation[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['donations', filterStatus],
    queryFn: () => api.getDonations({ status: filterStatus === 'all' ? undefined : filterStatus }),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (data?.donations) {
      setLiveDonations(data.donations);
    }
  }, [data]);

  // WebSocket Live Updates
  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = import.meta.env.VITE_WS_URL || `${wsProto}//${window.location.host}/v1/ws/donations`;
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsHost);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'donation_created' && payload.donation) {
            setLiveDonations((prev) => [payload.donation, ...prev]);
          } else if (payload.type === 'donation_updated' && payload.donation) {
            setLiveDonations((prev) =>
              prev.map((d) => (d.id === payload.donation.id ? payload.donation : d))
            );
          }
        } catch {
          // ignore non-json
        }
      };
    } catch {
      // WS fallback to polling
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Live Rescue Stream</h1>
          <p className="text-sm text-slate-500">
            Real-time feed of food surplus captured, classified, and routed across Austin
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm bg-white border border-slate-300 rounded-lg px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open (Available)</option>
            <option value="matched">Matched (Assigned)</option>
            <option value="picked_up">Picked Up (Rescued)</option>
            <option value="draft">Draft (Analyzing)</option>
          </select>

          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefetching ? 'animate-spin text-brand-600' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {isLoading && liveDonations.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-5 animate-pulse space-y-3">
              <div className="h-4 bg-slate-200 rounded w-1/3"></div>
              <div className="h-6 bg-slate-200 rounded w-2/3"></div>
              <div className="h-32 bg-slate-100 rounded-lg"></div>
            </div>
          ))}
        </div>
      ) : liveDonations.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <Package className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No donations found</h3>
          <p className="text-sm text-slate-500 mt-1">
            New food surplus posts will stream here live as soon as donors upload photos.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {liveDonations.map((donation) => (
            <div
              key={donation.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col"
            >
              <div className="p-5 flex-1 space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-slate-900 text-lg capitalize">
                      {donation.item.replace('_', ' ')}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5">
                      <User className="w-3.5 h-3.5" />
                      <span>{donation.donor_name || 'Austin Community Partner'}</span>
                    </div>
                  </div>
                  <StatusBadge status={donation.status} />
                </div>

                <div className="flex flex-wrap gap-2">
                  <FreshnessBadge grade={donation.freshness} confidence={donation.freshness_confidence} />
                  <HazardBadge flag={donation.hazard_flag} />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div>
                    <span className="text-slate-400 block">Est. Weight</span>
                    <span className="font-semibold text-slate-800 text-sm">{donation.est_weight_kg} kg</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Item Confidence</span>
                    <span className="font-semibold text-slate-800 text-sm">
                      {Math.round(donation.item_confidence * 100)}%
                    </span>
                  </div>
                </div>

                {donation.needs_review && (
                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Flagged for Human Review Queue</span>
                  </div>
                )}
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{new Date(donation.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <span className="font-mono text-[11px] text-slate-400">ID: {donation.id.slice(0, 8)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

