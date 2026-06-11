import { PaymentStatus } from "../types";
import { fmtDate } from "../utils";
import { ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";
import { useDashboardSummary, usePayments } from "../api/queries";

interface DashboardViewProps {
  onSelectPayment: (id: string) => void;
  onNavigateToPayments: () => void;
}

export default function DashboardView({
  onSelectPayment,
  onNavigateToPayments,
}: DashboardViewProps) {
  const { data: dashboard, isLoading: loadingSummary } = useDashboardSummary();
  const { data: payments = [], isLoading: loadingPayments } = usePayments({ limit: 8 });

  const isLoading = loadingSummary || loadingPayments;
  const paymentsData = dashboard?.payments;
  const recentPayments = payments.slice(0, 8);

  const totalCount = paymentsData?.total_payments ?? payments.length;
  const confirmedCount = paymentsData?.confirmed_count ?? 0;
  const pendingCount = paymentsData?.pending_count ?? 0;
  const totalVolumeWei = paymentsData?.total_volume_wei
    ? parseInt(paymentsData.total_volume_wei, 10)
    : payments.reduce((sum, p) => sum + parseInt(p.amount_wei || "0", 10), 0);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
      case 'paid':
      case 'settled':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            {status}
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 border border-amber-100">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
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

  if (isLoading) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-bold text-brand-text">Dashboard</h1>
            <p className="text-xs text-brand-muted">Aggregated summary of processing activities.</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 rounded-xl border border-brand-border bg-brand-surface animate-pulse" />
          ))}
        </div>
      </motion.div>
    );
  }

  const successRate = totalCount > 0 ? Math.round((confirmedCount / totalCount) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-brand-text">Dashboard</h1>
          <p className="text-xs text-brand-muted">Aggregated summary of processing activities.</p>
        </div>
        {dashboard && (
          <span className="inline-flex items-center self-start rounded-full bg-brand-surface px-2.5 py-1 text-xs font-medium text-brand-muted border border-brand-border">
            Updated: {fmtDate(new Date(dashboard.generated_at))}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex items-start justify-between rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm">
          <div className="space-y-3">
            <span className="text-xs font-semibold text-brand-muted tracking-wide uppercase">Total Payments</span>
            <p className="text-3xl font-bold tracking-tight text-brand-text">{totalCount.toLocaleString()}</p>
            <p className="text-xs text-brand-dim">+12% vs last month</p>
          </div>
        </div>
        <div className="flex items-start justify-between rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm">
          <div className="space-y-3">
            <span className="text-xs font-semibold text-brand-muted tracking-wide uppercase">Confirmed</span>
            <p className="text-3xl font-bold tracking-tight text-brand-text">{confirmedCount.toLocaleString()}</p>
            <p className="text-xs text-brand-dim">{successRate}% success rate</p>
          </div>
        </div>
        <div className="flex items-start justify-between rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm">
          <div className="space-y-3">
            <span className="text-xs font-semibold text-brand-muted tracking-wide uppercase">Pending Process</span>
            <p className="text-3xl font-bold tracking-tight text-brand-text">{pendingCount.toLocaleString()}</p>
            <p className="text-xs text-brand-dim">Awaiting confirmation</p>
          </div>
        </div>
        <div className="flex items-start justify-between rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm">
          <div className="space-y-3">
            <span className="text-xs font-semibold text-brand-muted tracking-wide uppercase">Network Volume</span>
            <p className="text-3xl font-bold tracking-tight text-brand-text">
              {(totalVolumeWei / 1000).toFixed(1)}k
              <span className="text-xs font-normal text-brand-muted ml-1">Wei</span>
            </p>
            <p className="text-xs text-brand-dim">Across all indexers</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-brand-border bg-white px-5 py-4">
          <h2 className="text-sm font-semibold text-brand-text">Recent Payments</h2>
          <button
            onClick={onNavigateToPayments}
            className="inline-flex items-center gap-1 rounded-md border border-brand-border-dark px-2.5 py-1 text-xs font-medium text-brand-text shadow-sm hover:bg-brand-bg transition-colors cursor-pointer"
          >
            View All
            <ArrowUpRight className="h-3 w-3" />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-brand-border bg-brand-bg/50 text-[11px] font-semibold tracking-wider text-brand-muted uppercase">
                <th className="px-5 py-3">Payment ID</th>
                <th className="px-5 py-3">Chain</th>
                <th className="px-5 py-3">Address</th>
                <th className="px-5 py-3 text-right">Amount (Wei)</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border font-sans text-xs">
              {recentPayments.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => onSelectPayment(p.id)}
                  className="group hover:bg-brand-bg/40 cursor-pointer transition-colors"
                >
                  <td className="px-5 py-3.5 font-mono text-brand-text font-medium select-all">{p.id}</td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex items-center rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-bold text-zinc-800 tracking-wide uppercase">{p.chain}</span>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-brand-muted select-all">
                    {p.address.slice(0, 10)}…{p.address.slice(-6)}
                  </td>
                  <td className="px-5 py-3.5 text-right font-mono text-brand-text font-semibold">
                    {parseInt(p.amount_wei || "0").toLocaleString()}
                  </td>
                  <td className="px-5 py-3.5">{getStatusBadge(p.status)}</td>
                  <td className="px-5 py-3.5 text-brand-muted">{fmtDate(new Date(p.created_at))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}