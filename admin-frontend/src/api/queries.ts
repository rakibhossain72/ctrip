import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiGet } from "./client";
import { Payment, ApiKey } from "../types";

// Query Keys
export const queryKeys = {
  dashboard: ["dashboard"] as const,
  payments: ["payments"] as const,
  payment: (id: string) => ["payments", id] as const,
  apiKeys: ["apiKeys"] as const,
  analytics: ["analytics"] as const,
};

// Dashboard Summary - single endpoint for everything
export function useDashboardSummary() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => apiGet<DashboardSummary>("/admin/analytics/summary"),
    staleTime: 30000,
  });
}

// All payments with filters
export function usePayments(filters?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: [...queryKeys.payments, filters],
    queryFn: () =>
      apiGet<Payment[]>("/admin/analytics/payments/recent", filters),
    staleTime: 30000,
  });
}

// Single Payment Detail (includes transactions and webhooks)
export function usePayment(id: string) {
  return useQuery({
    queryKey: queryKeys.payment(id),
    queryFn: () =>
      apiGet<PaymentDetailResponse>(`/admin/analytics/payments/${id}`),
    enabled: !!id,
    staleTime: 10000,
  });
}

// Fetch API Keys
export function useApiKeys() {
  return useQuery({
    queryKey: queryKeys.apiKeys,
    queryFn: () => apiGet<ApiKeyResponse[]>("/admin/api-keys"),
    staleTime: 60000,
  });
}

// Payment Volume Stats
export function usePaymentVolume() {
  return useQuery({
    queryKey: [...queryKeys.analytics, "volume"],
    queryFn: () =>
      apiGet<PaymentVolumeSummary>("/admin/analytics/payments/volume"),
    staleTime: 60000,
  });
}

// Daily Volume
export function useDailyVolume(days: number = 30) {
  return useQuery({
    queryKey: [...queryKeys.analytics, "daily", days],
    queryFn: () =>
      apiGet<DailyVolume[]>("/admin/analytics/payments/daily", { days }),
    staleTime: 60000,
  });
}

// Payments by Chain
export function usePaymentsByChain() {
  return useQuery({
    queryKey: [...queryKeys.analytics, "byChain"],
    queryFn: () =>
      apiGet<ChainBreakdown[]>("/admin/analytics/payments/by-chain"),
    staleTime: 60000,
  });
}

// Webhook Stats
export function useWebhookStats() {
  return useQuery({
    queryKey: [...queryKeys.analytics, "webhooks"],
    queryFn: () => apiGet<WebhookStats>("/admin/analytics/webhooks"),
    staleTime: 60000,
  });
}

// Transaction Stats
export function useTransactionStats() {
  return useQuery({
    queryKey: [...queryKeys.analytics, "transactions"],
    queryFn: () => apiGet<TransactionStats>("/admin/analytics/transactions"),
    staleTime: 60000,
  });
}

// Invalidate queries
export function useInvalidatePayments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.payments });
}

export function useInvalidateApiKeys() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
}

export function useInvalidateDashboard() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
}

// Types from OpenAPI spec
interface DashboardSummary {
  generated_at: string;
  payments: PaymentVolumeSummary;
  transactions: TransactionStats;
  webhooks: WebhookStats;
  api_keys: ApiKeyStats;
}

interface PaymentVolumeSummary {
  total_payments: number;
  total_volume_wei: string;
  confirmed_volume_wei: string;
  pending_count: number;
  confirmed_count: number;
  expired_count: number;
  failed_count: number;
  settled_count: number;
  by_status: PaymentCountByStatus[];
}

interface PaymentCountByStatus {
  status: string;
  count: number;
}

interface TransactionStats {
  total_transactions: number;
  confirmed: number;
  pending: number;
  failed: number;
}

interface WebhookStats {
  total_attempts: number;
  successful: number;
  failed: number;
  pending: number;
  success_rate: number;
  total_retries: number;
}

interface ApiKeyStats {
  total_keys: number;
  active_keys: number;
  revoked_keys: number;
  recently_used: number;
}

interface DailyVolume {
  date: string;
  count: number;
  volume_wei: string;
}

interface ChainBreakdown {
  chain: string;
  count: number;
  volume_wei: string;
}

interface PaymentDetailResponse {
  id: string;
  chain: string;
  address: string;
  amount_wei: string;
  status: string;
  confirmations: number;
  detected_in_block: number | null;
  token_id: string | null;
  created_at: string;
  expires_at: string;
  transactions: TransactionDetail[];
  webhooks: WebhookAttemptDetail[];
}

interface TransactionDetail {
  id: string;
  tx_hash: string;
  block_number: number | null;
  confirmations: number;
  status: string;
}

interface WebhookAttemptDetail {
  id: string;
  event_type: string;
  webhook_url: string;
  status: string;
  retry_count: number;
  last_error: string | null;
  next_retry_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiKeyResponse {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}
