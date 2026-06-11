import { useState, useMemo } from 'react';
import { PaymentStatus, ChainType } from '../types';
import { fmtDate } from '../utils';
import { Search, SlidersHorizontal, ArrowLeftRight } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { usePayments } from '../api/queries';

interface PaymentsViewProps {
  onSelectPayment: (id: string) => void;
}

export default function PaymentsView({ onSelectPayment }: PaymentsViewProps) {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [chainFilter, setChainFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const { data: allPayments = [], isLoading } = usePayments({ limit: 100 });

  const filteredPayments = useMemo(() => {
    return allPayments.filter((p) => {
      const matchStatus = statusFilter ? p.status === statusFilter : true;
      const matchChain = chainFilter ? p.chain === chainFilter : true;
      const matchSearch = searchQuery
        ? p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.amount_wei.includes(searchQuery)
        : true;
      return matchStatus && matchChain && matchSearch;
    });
  }, [allPayments, statusFilter, chainFilter, searchQuery]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
      case 'paid':
      case 'settled':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            {status}
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 border border-amber-100">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
            {status}
          </span>
        );
      case 'detected':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700 border border-sky-100">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse"></span>
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

  if (isLoading) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
        <div className="h-8 w-48 bg-brand-surface animate-pulse rounded" />
        <div className="h-12 bg-brand-surface animate-pulse rounded-xl" />
        <div className="h-64 bg-brand-surface animate-pulse rounded-xl" />
      </motion.div>
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
      <div>
        <h1 className="text-xl font-bold text-brand-text">Payments Feed</h1>
        <p className="text-xs text-brand-muted">Real-time ledger of deposit records and status updates.</p>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-brand-border bg-brand-surface p-4 shadow-sm sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute top-2.5 left-3 h-4 w-4 text-brand-muted" />
          <input
            type="text"
            placeholder="Search by Payment ID or Address..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-brand-border-dark bg-brand-surface py-2 pr-4 pl-9 text-xs text-brand-text placeholder-brand-dim focus:border-brand-accent focus:outline-none transition-all"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-brand-muted hidden sm:inline" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-xs text-brand-text focus:border-brand-accent focus:outline-none cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="detected">Detected</option>
            <option value="confirmed">Confirmed</option>
            <option value="paid">Paid</option>
            <option value="settled">Settled</option>
            <option value="expired">Expired</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={chainFilter}
            onChange={(e) => setChainFilter(e.target.value)}
            className="rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-xs text-brand-text focus:border-brand-accent focus:outline-none cursor-pointer"
          >
            <option value="">All Chains</option>
            <option value="bsc">BSC</option>
            <option value="polygon">Polygon</option>
            <option value="base">Base</option>
            <option value="avalanche">Avalanche</option>
          </select>
        </div>
      </div>

      <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-brand-border bg-brand-bg/50 text-[11px] font-semibold tracking-wider text-brand-muted uppercase">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Network</th>
                <th className="px-5 py-3">Deposit Address</th>
                <th className="px-5 py-3 text-right">Amount (Wei)</th>
                <th className="px-5 py-3">Confirmations</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border font-sans text-xs">
              <AnimatePresence mode="popLayout">
                {filteredPayments.length > 0 ? (
                  filteredPayments.map((p) => (
                    <motion.tr
                      layoutId={`row-${p.id}`}
                      key={p.id}
                      onClick={() => onSelectPayment(p.id)}
                      className="group hover:bg-brand-bg/40 cursor-pointer transition-colors"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                    >
                      <td className="px-5 py-3.5 font-mono text-brand-text font-medium select-all">{p.id.slice(0, 8)}…</td>
                      <td className="px-5 py-3.5">
                        <span className="inline-flex items-center rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-bold text-zinc-800 tracking-wide uppercase">{p.chain}</span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-brand-muted select-all">
                        {p.address.slice(0, 16)}…{p.address.slice(-6)}
                      </td>
                      <td className="px-5 py-3.5 text-right font-mono text-brand-text font-semibold">
                        {parseInt(p.amount_wei || '0').toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-brand-text">
                        <div className="flex items-center gap-1">
                          <ArrowLeftRight className="h-3 w-3 text-brand-dim" />
                          <span className="font-mono">{p.confirmations}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">{getStatusBadge(p.status)}</td>
                      <td className="px-5 py-3.5 text-brand-muted">{fmtDate(new Date(p.created_at))}</td>
                    </motion.tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-5 py-12 text-center text-brand-muted">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <SlidersHorizontal className="h-8 w-8 text-brand-dim" />
                        <span className="font-semibold text-sm">No transactions found</span>
                        <span className="text-[11px] text-brand-dim">Try adjusting your active status or chain filters.</span>
                      </div>
                    </td>
                  </tr>
                )}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}