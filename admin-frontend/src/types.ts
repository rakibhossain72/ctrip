export enum PaymentStatus {
  PENDING = 'pending',
  DETECTED = 'detected',
  CONFIRMED = 'confirmed',
  PAID = 'paid',
  SETTLED = 'settled',
  EXPIRED = 'expired',
  FAILED = 'failed',
}

export enum ChainType {
  BSC = 'bsc',
  POLYGON = 'polygon',
  BASE = 'base',
  AVALANCH = 'avalanche',
}

export interface Payment {
  id: string;
  chain: string;
  address: string;
  amount_wei: string;
  status: string;
  confirmations: number;
  created_at: string;
  expires_at: string;
  detected_in_block?: number | null;
  token_id?: string | null;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ToastMessage {
  id: string;
  message: string;
  type: 'ok' | 'err';
}

export interface Transaction {
  id: string;
  tx_hash: string;
  block_number?: number | null;
  confirmations: number;
  status: string;
}

export interface WebhookAttempt {
  id: string;
  event_type: string;
  webhook_url: string;
  status: string;
  retry_count: number;
  last_error?: string | null;
  next_retry_at?: string | null;
  created_at: string;
  updated_at: string;
}