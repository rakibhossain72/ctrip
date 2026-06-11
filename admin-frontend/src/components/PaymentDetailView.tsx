import { useState, useEffect } from 'react';
import { ArrowLeft, Copy, Check } from 'lucide-react';
import { motion } from 'motion/react';
import { usePayment } from '../api/queries';
import { useSendWebhook, useSweepAddress, useTriggerScan } from '../api/mutations';

interface PaymentDetailViewProps {
  paymentId: string;
  onBack: () => void;
  triggerToast: (msg: string, type?: 'ok' | 'err') => void;
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' });

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'confirmed':
    case 'paid':
    case 'settled':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
          {status}
        </span>
      );
    case 'pending':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 border border-amber-100">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse"></span>
          {status}
        </span>
      );
    case 'detected':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700 border border-sky-100">
          <span className="h-1.5 w-1.5 rounded-full bg-sky-500 animate-pulse"></span>
          {status}
        </span>
      );
    case 'expired':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600 border border-gray-200">
          {status}
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700 border border-red-100">
          {status}
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-700">
          {status}
        </span>
      );
  }
};

const getTransactionBadge = (status: string) => {
  if (status === 'confirmed') {
    return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-100">{status}</span>;
  }
  if (status === 'failed') {
    return <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-700 border border-red-100">{status}</span>;
  }
  return <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 border border-amber-100">{status}</span>;
};

export default function PaymentDetailView({ paymentId, onBack, triggerToast }: PaymentDetailViewProps) {
  const { data: payment, isLoading, error } = usePayment(paymentId);
  const [copied, setCopied] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [showSweep, setShowSweep] = useState(false);
  const [webhookEvent, setWebhookEvent] = useState('payment.confirmed');
  const [webhookResult, setWebhookResult] = useState<string | null>(null);
  const [sweepResult, setSweepResult] = useState<string | null>(null);
  const [sweepChain, setSweepChain] = useState<string>(payment?.chain || 'bsc');

  const triggerScan = useTriggerScan();
  const sendWebhook = useSendWebhook();
  const sweepAddress = useSweepAddress();

  const isTerminated = ['expired', 'failed'].includes(payment?.status || '');
  const progressPercent = isTerminated ? 0 : Math.min(100, (timeLeft / 1800) * 100);

  useEffect(() => {
    if (!payment?.expires_at) return;
    const calculateTimeLeft = () => {
      const exp = new Date(payment.expires_at!).getTime();
      const now = Date.now();
      return Math.max(0, Math.floor((exp - now) / 1000));
    };
    setTimeLeft(calculateTimeLeft());
    if (isTerminated) return;
    const interval = window.setInterval(() => {
      const remaining = calculateTimeLeft();
      setTimeLeft(remaining);
      if (remaining <= 0) window.clearInterval(interval);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [payment?.expires_at, isTerminated]);

  const copyAddress = async () => {
    if (!payment) return;
    try {
      await navigator.clipboard.writeText(payment.address);
      setCopied(true);
      triggerToast('Address copied', 'ok');
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      triggerToast('Failed to copy address', 'err');
    }
  };

  const handleScan = async () => {
    try {
      const result = await triggerScan.mutateAsync();
      setWebhookResult(result.message);
      triggerToast(result.message, 'ok');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Scan failed';
      setWebhookResult(message);
      triggerToast(message, 'err');
    }
  };

  const handleSweep = async () => {
    if (!payment) return;
    try {
      const result = await sweepAddress.mutateAsync({ address: payment.address, chain_name: sweepChain });
      setSweepResult(result.message);
      triggerToast(result.message, 'ok');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Sweep failed';
      setSweepResult(message);
      triggerToast(message, 'err');
    }
  };

  const handleWebhook = async () => {
    try {
      const result = await sendWebhook.mutateAsync({ payment_id: paymentId, event_type: webhookEvent });
      setWebhookResult(result.message);
      triggerToast(result.message, 'ok');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Webhook failed';
      setWebhookResult(message);
      triggerToast(message, 'err');
    }
  };

  const formatTimeLeft = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-brand-muted">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-brand-border border-t-brand-accent mb-4" />
        <p className="text-xs font-medium">Retrieving transaction details...</p>
      </div>
    );
  }

  if (error || !payment) {
    return (
      <div className="rounded-2xl border border-brand-border bg-brand-surface p-8 text-sm text-brand-dim">
        Payment not found.
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      <div className="flex items-center gap-2 text-xs text-brand-muted">
        <button onClick={onBack} className="inline-flex items-center gap-1 hover:text-brand-text transition-colors cursor-pointer font-semibold">
          <ArrowLeft className="h-3 w-3" /> Back to Payments
        </button>
        <span className="text-brand-dim">/</span>
        <span className="font-mono text-brand-dim select-all">{payment.id}</span>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-brand-text">Payment Detail</h1>
          <p className="text-xs text-brand-muted">Created {formatDate(payment.created_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          {getStatusBadge(payment.status)}
          <a className="inline-flex items-center gap-1 rounded-md border border-brand-border-dark px-2.5 py-1 text-xs font-medium text-brand-text shadow-sm hover:bg-brand-bg transition-colors cursor-pointer" href={`/payment/${payment.id}`} target="_blank" rel="noreferrer">
            Public Page ↗
          </a>
        </div>
      </div>

      {!isTerminated && payment.status === 'pending' && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/30 p-4 flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-xs text-amber-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span>Awaiting payment detection. Session expires in <span className="font-mono font-bold">{formatTimeLeft(timeLeft)}</span></span>
          </div>
          <div className="w-full sm:w-48 bg-amber-100 rounded-full h-1.5 overflow-hidden">
            <div className="bg-amber-500 h-1.5 rounded-full transition-all duration-1000 ease-linear" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-brand-border bg-white px-5 py-4">
              <h2 className="text-sm font-semibold text-brand-text flex items-center gap-2">Payment Information</h2>
            </div>
            <div className="px-5 py-2 divide-y divide-brand-border text-xs font-sans">
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Chain</span>
                <span className="inline-flex items-center rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-bold text-zinc-800 tracking-wide uppercase">{payment.chain}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Deposit Address</span>
                <div className="flex items-center gap-2 justify-end">
                  <span className="font-mono text-brand-muted text-xs truncate max-w-[160px] sm:max-w-xs" title={payment.address}>
                    {payment.address}
                  </span>
                  <button type="button" onClick={copyAddress} className="inline-flex items-center gap-1 rounded border border-brand-border-dark bg-white px-2 py-1 text-[10px] font-semibold text-brand-text hover:bg-brand-bg transition-colors cursor-pointer">
                    {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Amount (Wei)</span>
                <span className="font-mono text-brand-text font-semibold">{parseInt(payment.amount_wei || '0').toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Confirmations</span>
                <span className="font-mono text-brand-text font-semibold">{payment.confirmations}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Detected in Block</span>
                <span className="font-mono text-brand-text">{payment.detected_in_block ?? '—'}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Token ID</span>
                <span className="font-mono text-brand-text">{payment.token_id ?? '—'}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Created At</span>
                <span className="text-brand-text">{formatDate(payment.created_at)}</span>
              </div>
              <div className="flex justify-between items-center py-3 gap-4">
                <span className="text-brand-muted font-medium">Expires At</span>
                <span className="text-brand-text">{formatDate(payment.expires_at)}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-brand-border bg-white px-5 py-4">
              <h2 className="text-sm font-semibold text-brand-text flex items-center gap-2">Transactions Ledger</h2>
              <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-semibold text-zinc-800 border border-zinc-200">
                {payment.transactions?.length ?? 0}
              </span>
            </div>
            <div className="px-5 py-2 divide-y divide-brand-border">
              {payment.transactions?.length ? (
                payment.transactions.map(tx => (
                  <div className="flex justify-between items-center py-3 text-xs gap-4" key={tx.id}>
                    <div className="flex flex-col gap-1 min-w-0">
                      <span className="font-mono text-brand-text font-medium select-all break-all pr-4 truncate" title={tx.tx_hash}>{tx.tx_hash}</span>
                      <div className="text-[10px] text-brand-muted">Block {tx.block_number ?? '?'} · {tx.confirmations} confirmations</div>
                    </div>
                    <div className="shrink-0">{getTransactionBadge(tx.status)}</div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-xs text-brand-muted">No transactions recorded yet.</div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-brand-border bg-white px-5 py-4">
              <h2 className="text-sm font-semibold text-brand-text flex items-center gap-2">Webhook Dispatches</h2>
              <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-semibold text-zinc-800 border border-zinc-200">
                {payment.webhooks?.length ?? 0}
              </span>
            </div>
            <div className="px-5 py-4">
              {payment.webhooks?.length ? (
                <div className="space-y-4">
                  {payment.webhooks.map((wh, index) => (
                    <div className="relative flex gap-4" key={wh.id}>
                      <div className="flex flex-col items-center shrink-0">
                        <div className={`h-2.5 w-2.5 rounded-full border-2 ${wh.status === 'success' ? 'bg-emerald-500 border-emerald-200' : wh.status === 'failed' ? 'bg-red-500 border-red-200' : 'bg-amber-500 border-amber-200 animate-pulse'}`} />
                        {index < (payment.webhooks?.length ?? 0) - 1 && <div className="w-px flex-1 bg-brand-border my-1.5" />}
                      </div>
                      <div className="flex-1 pb-2 text-xs min-w-0">
                        <div className="flex items-center justify-between gap-4 mb-1.5">
                          <span className="font-semibold text-brand-text">{wh.event_type}</span>
                          <span className="text-[10px] text-brand-dim font-mono">{formatDate(wh.created_at)}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-[11px] text-brand-muted">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${wh.status === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : wh.status === 'failed' ? 'bg-red-50 text-red-700 border-red-100' : 'bg-zinc-100 text-zinc-500 border-zinc-200'}`}>
                            {wh.status}
                          </span>
                          <span>·</span>
                          <span>{wh.retry_count} retr{wh.retry_count === 1 ? 'y' : 'ies'}</span>
                          <span>·</span>
                          <span className="font-mono select-all truncate max-w-[140px] sm:max-w-xs" title={wh.webhook_url}>{wh.webhook_url}</span>
                        </div>
                        {wh.last_error && (
                          <div className="mt-2 text-[11px] text-red-600 font-medium bg-red-50/50 border border-red-100 rounded-md p-2 break-all">✕ {wh.last_error}</div>
                        )}
                        {wh.next_retry_at && (
                          <div className="mt-1 text-[10px] text-brand-dim">Next retry: {formatDate(wh.next_retry_at)}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-brand-muted">No webhook attempts yet.</div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden p-5 space-y-4">
            <h3 className="text-sm font-semibold text-brand-text flex items-center gap-2 pb-3 border-b border-brand-border">Operations Control</h3>
            <div className="flex flex-col gap-2">
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-brand-border-dark bg-white px-3 py-2 text-xs font-semibold text-brand-text hover:bg-brand-bg active:scale-[0.98] transition-all cursor-pointer"
                type="button"
                onClick={handleScan}
                disabled={triggerScan.isPending}
              >
                ⟳ &nbsp;{triggerScan.isPending ? 'Scanning...' : 'Scan Deposit Status'}
              </button>
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-brand-border-dark bg-white px-3 py-2 text-xs font-semibold text-brand-text hover:bg-brand-bg active:scale-[0.98] transition-all cursor-pointer"
                type="button"
                onClick={() => setShowSweep(!showSweep)}
              >
                ↑ &nbsp;Sweep Address Assets
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden p-5 space-y-4">
            <h3 className="text-sm font-semibold text-brand-text flex items-center gap-2 pb-3 border-b border-brand-border">Dispatch Event Webhook</h3>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-brand-muted">Select Event Type</label>
                <select
                  className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-xs text-brand-text focus:border-brand-accent focus:outline-none transition-all cursor-pointer"
                  value={webhookEvent}
                  onChange={e => setWebhookEvent(e.target.value)}
                >
                  <option value="payment.confirmed">payment.confirmed</option>
                  <option value="payment.expired">payment.expired</option>
                  <option value="payment.swept">payment.swept</option>
                </select>
              </div>
              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-accent px-3 py-2 text-xs font-semibold text-white shadow-sm hover:opacity-90 active:scale-[0.98] transition-all cursor-pointer"
                type="button"
                onClick={handleWebhook}
                disabled={sendWebhook.isPending}
              >
                {sendWebhook.isPending ? 'Sending...' : 'Send Trigger'}
              </button>
              {webhookResult && (
                <div className="text-[11px] bg-brand-bg border border-brand-border rounded-lg p-2.5 font-mono text-brand-muted break-all">{webhookResult}</div>
              )}
            </div>
          </div>

          {showSweep && (
            <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden p-5 space-y-4">
              <h3 className="text-sm font-semibold text-brand-text flex items-center gap-2 pb-3 border-b border-brand-border">Sweep Address Details</h3>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold text-brand-muted">Target Blockchain Network</label>
                  <input
                    className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-xs text-brand-text focus:border-brand-accent focus:outline-none transition-colors"
                    value={sweepChain}
                    onChange={e => setSweepChain(e.target.value)}
                    placeholder="e.g. ethereum"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-accent px-3 py-2 text-xs font-semibold text-white shadow-sm hover:opacity-90 active:scale-[0.98] transition-all cursor-pointer"
                    type="button"
                    onClick={handleSweep}
                    disabled={sweepAddress.isPending}
                  >
                    {sweepAddress.isPending ? 'Sweeping...' : 'Sweep'}
                  </button>
                  <button
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-brand-border bg-white px-3 py-2 text-xs font-semibold text-brand-muted hover:bg-brand-bg active:scale-[0.98] transition-all cursor-pointer"
                    type="button"
                    onClick={() => setShowSweep(false)}
                  >
                    Cancel
                  </button>
                </div>
                {sweepResult && (
                  <div className="text-[11px] bg-brand-bg border border-brand-border rounded-lg p-2.5 font-mono text-brand-muted break-all">{sweepResult}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}