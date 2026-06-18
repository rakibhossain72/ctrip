import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import { queryKeys } from './queries';

// Create API Key - returns raw_key only on creation
export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string) => {
      return api<ApiKeyCreatedResponse>('/admin/api-keys', {
        method: 'POST',
        body: { name },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
    },
  });
}

// Revoke API Key
export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api(`/admin/api-keys/${id}`, {
        method: 'DELETE',
      });
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
    },
  });
}

// Trigger Payment Scan
export function useTriggerScan() {
  return useMutation({
    mutationFn: async () => {
      const result = await api<JobResponse>('/admin/scan-now', {
        method: 'POST',
      });
      return result;
    },
  });
}

// Trigger Fund Sweep (all chains)
export function useTriggerSweep() {
  return useMutation({
    mutationFn: async () => {
      const result = await api<JobResponse>('/admin/sweep-now', {
        method: 'POST',
      });
      return result;
    },
  });
}

// Sweep Specific Address
export function useSweepAddress() {
  return useMutation({
    mutationFn: async ({
      address,
      chain_name,
    }: {
      address: string;
      chain_name: string;
    }) => {
      return api<JobResponse>('/admin/sweep-address', {
        method: 'POST',
        body: { address, chain_name },
      });
    },
  });
}

// Process Payment Manually
export function useProcessPayment() {
  return useMutation({
    mutationFn: async ({
      payment_id,
      chain_name,
    }: {
      payment_id: string;
      chain_name: string;
    }) => {
      return api<JobResponse>('/admin/process-payment', {
        method: 'POST',
        body: { payment_id, chain_name },
      });
    },
  });
}

// Send Webhook for Payment
export function useSendWebhook() {
  return useMutation({
    mutationFn: async ({
      payment_id,
      event_type,
    }: {
      payment_id: string;
      event_type: string;
    }) => {
      return api<JobResponse>(
        `/admin/send-webhook?payment_id=${payment_id}&event_type=${event_type}`,
        { method: 'POST' }
      );
    },
  });
}

// Send Custom Webhook
export function useSendCustomWebhook() {
  return useMutation({
    mutationFn: async ({
      url,
      payload,
      secret,
    }: {
      url: string;
      payload: Record<string, unknown>;
      secret?: string;
    }) => {
      return api<JobResponse>('/admin/custom-webhook', {
        method: 'POST',
        body: { url, payload, secret },
      });
    },
  });
}

// Create Payment (public endpoint)
export function useCreatePayment() {
  return useMutation({
    mutationFn: async ({
      amount,
      chain,
      token_contract_address,
    }: {
      amount: number;
      chain: string;
      token_contract_address?: string;
    }) => {
      return api<PaymentRead>('/api/v1/payments/', {
        method: 'POST',
        body: { amount, chain, token_contract_address },
      });
    },
  });
}

// Types from OpenAPI spec
interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  raw_key: string; // Only returned on creation
}

interface JobResponse {
  job_id: string;
  status: string;
  message: string;
}

interface PaymentRead {
  id: string;
  chain: string;
  address: string;
  amount: string;
  status: string;
  confirmations: number;
  created_at: string;
  expires_at: string;
  token_contract_address?: string | null;
}