import React from 'react';
import type { DonationStatus, FreshnessGrade, HazardFlag } from '../types';

export const StatusBadge: React.FC<{ status: DonationStatus }> = ({ status }) => {
  const styles: Record<DonationStatus, string> = {
    draft: 'bg-slate-100 text-slate-700 border-slate-300',
    open: 'bg-emerald-50 text-emerald-700 border-emerald-300',
    matched: 'bg-blue-50 text-blue-700 border-blue-300',
    picked_up: 'bg-brand-100 text-brand-800 border-brand-300',
    cancelled: 'bg-rose-50 text-rose-700 border-rose-300',
    spoiled: 'bg-amber-50 text-amber-800 border-amber-300',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status] || styles.draft}`}>
      {status.replace('_', ' ').toUpperCase()}
    </span>
  );
};

export const FreshnessBadge: React.FC<{ grade: FreshnessGrade; confidence?: number }> = ({ grade, confidence }) => {
  const labels: Record<FreshnessGrade, { text: string; style: string }> = {
    grade_3_fresh: { text: 'Grade 3: Fresh', style: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
    grade_2_good: { text: 'Grade 2: Good', style: 'bg-teal-100 text-teal-800 border-teal-300' },
    grade_1_poor: { text: 'Grade 1: Marginal', style: 'bg-amber-100 text-amber-800 border-amber-300' },
    grade_0_spoiled: { text: 'Grade 0: Spoiled', style: 'bg-rose-100 text-rose-800 border-rose-300' },
  };

  const item = labels[grade] || { text: grade, style: 'bg-slate-100 text-slate-700' };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-medium border ${item.style}`}>
      <span>{item.text}</span>
      {confidence !== undefined && (
        <span className="text-[10px] opacity-75">({Math.round(confidence * 100)}%)</span>
      )}
    </span>
  );
};

export const HazardBadge: React.FC<{ flag: HazardFlag }> = ({ flag }) => {
  if (flag === 'none') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">
        Safe / No Hazard
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-rose-600 text-white animate-pulse shadow-sm">
      ⚠️ Contamination Hazard
    </span>
  );
};

