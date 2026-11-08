import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { Building2, CheckCircle2, XCircle, Phone, MapPin, Scale } from 'lucide-react';

export const Recipients: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: recipients, isLoading } = useQuery({
    queryKey: ['recipients'],
    queryFn: () => api.getRecipients(),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_accepting }: { id: string; is_accepting: boolean }) =>
      api.updateRecipientStatus(id, is_accepting),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipients'] });
    },
  });

  const defaultRecipients = recipients || [
    {
      id: 'r1',
      org_name: 'Central Texas Food Bank',
      address: '6500 Metropolis Dr, Austin, TX 78744',
      latitude: 30.2038,
      longitude: -97.7471,
      capacity_kg_per_day: 1500,
      is_accepting: true,
      accepted_items: ['produce_fruit', 'produce_vegetable', 'bread_bakery', 'dairy', 'grains_staples'],
      phone_e164: '+15125550100',
    },
    {
      id: 'r2',
      org_name: 'Caritas of Austin Community Kitchen',
      address: '611 Neches St, Austin, TX 78701',
      latitude: 30.2701,
      longitude: -97.7402,
      capacity_kg_per_day: 500,
      is_accepting: true,
      accepted_items: ['prepared_cooked', 'soup_stew', 'bread_bakery', 'meat_fish'],
      phone_e164: '+15125550101',
    },
    {
      id: 'r3',
      org_name: 'Hope Food Pantry Austin',
      address: '4001 Speedway, Austin, TX 78751',
      latitude: 30.3015,
      longitude: -97.7289,
      capacity_kg_per_day: 350,
      is_accepting: false,
      accepted_items: ['produce_fruit', 'produce_vegetable', 'grains_staples'],
      phone_e164: '+15125550102',
    },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Partner Shelters & Pantries</h1>
        <p className="text-sm text-slate-500">
          Manage recipient receiving capacity, diet preferences, and live intake status for autonomous matching
        </p>
      </div>

      {isLoading && !recipients ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-slate-200 animate-pulse h-32"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {defaultRecipients.map((recipient) => (
            <div
              key={recipient.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-5"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-brand-700">
                    <Building2 className="w-5 h-5" />
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      recipient.is_accepting
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                        : 'bg-rose-50 text-rose-700 border-rose-300'
                    }`}
                  >
                    {recipient.is_accepting ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Accepting Donations</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                        <span>Paused / Full</span>
                      </>
                    )}
                  </span>
                </div>

                <div>
                  <h3 className="font-bold text-slate-900 text-base">{recipient.org_name}</h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-1">
                    <MapPin className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                    <span className="truncate">{recipient.address}</span>
                  </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 flex items-center gap-1">
                      <Scale className="w-3.5 h-3.5 text-slate-400" />
                      <span>Daily Capacity:</span>
                    </span>
                    <span className="font-bold text-slate-800">{recipient.capacity_kg_per_day} kg/day</span>
                  </div>

                  {recipient.phone_e164 && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 flex items-center gap-1">
                        <Phone className="w-3.5 h-3.5 text-slate-400" />
                        <span>Dispatch Contact:</span>
                      </span>
                      <span className="font-mono text-slate-700">{recipient.phone_e164}</span>
                    </div>
                  )}
                </div>

                <div>
                  <span className="text-xs font-semibold text-slate-500 block mb-1.5">Accepted Food Categories</span>
                  <div className="flex flex-wrap gap-1.5">
                    {recipient.accepted_items.map((cat) => (
                      <span
                        key={cat}
                        className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700"
                      >
                        {cat.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-500">Autonomous Routing Intake:</span>
                <button
                  onClick={() =>
                    toggleMutation.mutate({
                      id: recipient.id,
                      is_accepting: !recipient.is_accepting,
                    })
                  }
                  className={`text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors ${
                    recipient.is_accepting
                      ? 'border-slate-300 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 text-slate-600'
                      : 'border-emerald-500 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                  }`}
                >
                  {recipient.is_accepting ? 'Pause Intake' : 'Resume Intake'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

