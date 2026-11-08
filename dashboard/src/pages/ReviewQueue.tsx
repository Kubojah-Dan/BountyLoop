import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ReviewQueueItem } from '../types';
import { CheckCircle, XCircle, AlertTriangle, HelpCircle, ShieldAlert } from 'lucide-react';

export const ReviewQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedItem, setSelectedItem] = useState<ReviewQueueItem | null>(null);
  const [resolutionAction, setResolutionAction] = useState<'approve' | 'correct' | 'reject'>('approve');
  const [correctedItem, setCorrectedItem] = useState<string>('produce_fruit');
  const [correctedFreshness, setCorrectedFreshness] = useState<string>('grade_2_good');
  const [notes, setNotes] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['review-queue'],
    queryFn: () => api.getReviewQueue('pending'),
    refetchInterval: 10000,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof api.resolveReviewItem>[1] }) =>
      api.resolveReviewItem(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['donations'] });
      setSelectedItem(null);
      setNotes('');
    },
  });

  const handleResolveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    resolveMutation.mutate({
      id: selectedItem.id,
      payload: {
        action: resolutionAction,
        notes: notes || undefined,
        item: resolutionAction === 'correct' ? correctedItem : undefined,
        freshness: resolutionAction === 'correct' ? correctedFreshness : undefined,
      },
    });
  };

  const queueItems = data?.items || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <div className="flex items-center space-x-2">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Human Review Queue</h1>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
            {queueItems.length} Pending
          </span>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Review donations flagged for low confidence, potential spoilage, or contamination. Approvals and corrections append directly to the ML retraining label store.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white p-6 rounded-xl border border-slate-200 animate-pulse h-28"></div>
          ))}
        </div>
      ) : queueItems.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">Queue is Clear</h3>
          <p className="text-sm text-slate-500 mt-1">
            Zero donations currently require manual verification. High confidence AI cascade is operating autonomously.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {queueItems.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-6"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="px-2.5 py-1 text-xs font-bold rounded-md bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    <span>{item.review_reason.replace('_', ' ').toUpperCase()}</span>
                  </span>
                  <span className="text-xs text-slate-400 font-mono">Queue ID: {item.id.slice(0, 8)}</span>
                </div>

                <div className="text-sm text-slate-700">
                  <span className="font-semibold text-slate-900">Donation ID: </span>
                  <span className="font-mono text-xs">{item.donation_id}</span>
                </div>

                <p className="text-xs text-slate-500">
                  Queued on {new Date(item.created_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setSelectedItem(item);
                    setResolutionAction('approve');
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm flex items-center gap-1.5"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Verify / Resolve</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Resolution Modal */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 border border-slate-200">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-lg font-bold text-slate-900">Resolve Review Queue Item</h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleResolveSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 mb-2">Resolution Action</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setResolutionAction('approve')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 ${
                      resolutionAction === 'approve'
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-500'
                        : 'bg-white text-slate-700 border-slate-200'
                    }`}
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>Approve AI</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setResolutionAction('correct')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 ${
                      resolutionAction === 'correct'
                        ? 'bg-blue-50 text-blue-800 border-blue-500'
                        : 'bg-white text-slate-700 border-slate-200'
                    }`}
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    <span>Correct Labels</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setResolutionAction('reject')}
                    className={`py-2 px-3 text-xs font-bold rounded-lg border flex items-center justify-center gap-1.5 ${
                      resolutionAction === 'reject'
                        ? 'bg-rose-50 text-rose-800 border-rose-500'
                        : 'bg-white text-slate-700 border-slate-200'
                    }`}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject / Hazard</span>
                  </button>
                </div>
              </div>

              {resolutionAction === 'correct' && (
                <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Correct Food Category</label>
                    <select
                      value={correctedItem}
                      onChange={(e) => setCorrectedItem(e.target.value)}
                      className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2"
                    >
                      <option value="produce_fruit">Produce: Fruit</option>
                      <option value="produce_vegetable">Produce: Vegetable</option>
                      <option value="bread_bakery">Bread & Bakery</option>
                      <option value="dairy">Dairy</option>
                      <option value="prepared_cooked">Prepared Meals</option>
                      <option value="meat_fish">Meat & Fish</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Correct Freshness Grade</label>
                    <select
                      value={correctedFreshness}
                      onChange={(e) => setCorrectedFreshness(e.target.value)}
                      className="w-full text-xs bg-white border border-slate-300 rounded-lg p-2"
                    >
                      <option value="grade_3_fresh">Grade 3: Fresh</option>
                      <option value="grade_2_good">Grade 2: Good</option>
                      <option value="grade_1_poor">Grade 1: Marginal</option>
                      <option value="grade_0_spoiled">Grade 0: Spoiled</option>
                    </select>
                  </div>
                </div>
              )}

              {resolutionAction === 'reject' && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Rejecting will cancel the donation and prevent routing to any food pantry.</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Operator Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Optional review notes..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-brand-500"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resolveMutation.isPending}
                  className="px-4 py-2 text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
                >
                  {resolveMutation.isPending ? 'Persisting...' : 'Submit Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

