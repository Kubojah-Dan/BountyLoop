import type { Donation, ImpactSummary, Recipient, ReviewQueueItem } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(
    public status: number,
    public title: string,
    public detail: string,
    public data?: unknown
  ) {
    super(detail || title);
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('bountyloop_auth_token') || 'mock_admin_token';
  const url = `${API_BASE}${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: { title?: string; detail?: string } = {};
    try {
      errorData = await response.json();
    } catch {
      // not JSON
    }
    throw new ApiError(
      response.status,
      errorData.title || 'Request Failed',
      errorData.detail || response.statusText,
      errorData
    );
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Donations
  getDonations: (params?: { status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    return request<{ donations: Donation[]; total: number }>(`/v1/donations?${query}`);
  },

  getDonation: (id: string) => request<Donation>(`/v1/donations/${id}`),

  confirmDonation: (id: string, payload: { item: string; freshness: string; est_weight_kg?: number }) =>
    request<Donation>(`/v1/donations/${id}/confirm`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  // Review Queue
  getReviewQueue: (status: string = 'pending') =>
    request<{ items: ReviewQueueItem[]; total: number }>(`/v1/review-queue?status=${status}`),

  resolveReviewItem: (id: string, payload: { action: 'approve' | 'correct' | 'reject'; notes?: string; item?: string; freshness?: string }) =>
    request<ReviewQueueItem>(`/v1/review-queue/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Impact
  getImpactSummary: () => request<ImpactSummary>('/v1/impact/summary'),

  // Recipients
  getRecipients: () => request<Recipient[]>('/v1/recipients'),

  updateRecipientStatus: (id: string, is_accepting: boolean) =>
    request<Recipient>(`/v1/recipients/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_accepting }),
    }),

  // Health / Metrics
  getHealth: (deep: boolean = false) => request<{ status: string; components?: Record<string, string> }>(`/healthz${deep ? '?deep=true' : ''}`),
};

