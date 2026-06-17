import React, { useState } from "react";
import { Network, ArrowLeftRight, BellRing, Settings } from "lucide-react";
import { motion } from "motion/react";

interface OperationsViewProps {
  key?: string;
  triggerToast: (msg: string, type?: "ok" | "err") => void;
}

export default function OperationsView({ triggerToast }: OperationsViewProps) {
  // Input states
  const [procId, setProcId] = useState("");
  const [procChain, setProcChain] = useState("bsc");
  const [procResult, setProcResult] = useState<string>("");
  const [procLoading, setProcLoading] = useState(false);

  const [sweepAddr, setSweepAddr] = useState("");
  const [sweepChain, setSweepChain] = useState("bsc");
  const [sweepResult, setSweepResult] = useState<string>("");
  const [sweepLoading, setSweepLoading] = useState(false);

  const [whId, setWhId] = useState("");
  const [whEvent, setWhEvent] = useState("payment.confirmed");
  const [whResult, setWhResult] = useState<string>("");
  const [whLoading, setWhLoading] = useState(false);

  // Handlers
  const handleProcess = (e: React.FormEvent) => {
    e.preventDefault();
    if (!procId.trim()) {
      triggerToast("Please provide a Payment ID", "err");
      return;
    }
    setProcLoading(true);
    setProcResult("Initiating process diagnostics...");

    setTimeout(() => {
      setProcLoading(false);
      setProcResult(
        JSON.stringify(
          {
            status: "ok",
            operation: "PROCESS_PAYMENT_DIAGNOSTICS",
            payment_id: procId,
            chain: procChain.toUpperCase(),
            gas_used: `${Math.floor(Math.random() * 45000) + 21000} weis`,
            block_number: Math.floor(Math.random() * 10000000) + 5000000,
            simulated_signatures: ["0x39aef...9a2e", "0x10bde...51da"],
            timestamp: new Date().toISOString(),
          },
          null,
          2,
        ),
      );
      triggerToast(
        "Payment verification diagnostics processed successfully",
        "ok",
      );
    }, 750);
  };

  const handleSweep = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sweepAddr.trim()) {
      triggerToast("Please verify target Sweep Address", "err");
      return;
    }
    setSweepLoading(true);
    setSweepResult("Broadcasting sweep payload to validator pool...");

    setTimeout(() => {
      setSweepLoading(false);
      setSweepResult(
        JSON.stringify(
          {
            status: "ok",
            operation: "ASSET_SWEEP",
            target_address: sweepAddr,
            network_chain: sweepChain.toUpperCase(),
            unlocked_balance_wei: `${Math.floor(Math.random() * 10000) + 1200} WEI`,
            sweep_transaction_hash: `0x${Array.from(
              { length: 64 },
              () => "0123456789abcdef"[Math.floor(Math.random() * 16)],
            ).join("")}`,
            gas_limit: "150000",
            state: "BROADCAST_SUCCESS",
            timestamp: new Date().toISOString(),
          },
          null,
          2,
        ),
      );
      triggerToast("Asset sweep broadcast complete", "ok");
    }, 800);
  };

  const handleWebhook = (e: React.FormEvent) => {
    e.preventDefault();
    if (!whId.trim()) {
      triggerToast("Webhook Event requires a Payment ID", "err");
      return;
    }
    setWhLoading(true);
    setWhResult("Queueing webhook broadcast in active sidecar daemon...");

    setTimeout(() => {
      setWhLoading(false);
      setWhResult(
        JSON.stringify(
          {
            status: "delivered",
            event: whEvent,
            destination_urls: [
              "https://api.ctrip-travel.com/v1/payments/verify",
              "https://admin.ctrip-internal.com/hooks/ledger",
            ],
            payload: {
              id: whId,
              event_type: whEvent,
              triggered_by: "CONSOLE_OPERATOR",
              timestamp: new Date().toISOString(),
              ledger_reference: `REF_${Math.floor(Math.random() * 899999) + 100000}`,
            },
            http_response_code: 200,
            response_body: { success: true },
            timestamp: new Date().toISOString(),
          },
          null,
          2,
        ),
      );
      triggerToast("System Webhook dispatched successfully", "ok");
    }, 650);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-xl font-bold text-brand-text">Operations Panel</h1>
        <p className="text-xs text-brand-muted">
          Trigger manual chain indexing, hotroom address sweeps, or mock
          webhooks.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Card 1: Process Payment */}
        <div className="rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-brand-bg pb-3">
            <ArrowLeftRight className="h-4.5 w-4.5 text-zinc-950" />
            <span className="text-sm font-semibold text-brand-text">
              Manually Process Signal
            </span>
          </div>

          <form
            onSubmit={handleProcess}
            className="space-y-4 text-xs font-semibold"
          >
            <div>
              <label htmlFor="proc-id" className="block text-brand-text mb-1">
                Payment UUID Sequence
              </label>
              <input
                id="proc-id"
                type="text"
                placeholder="e.g. 5eb3f-410a"
                value={procId}
                onChange={(e) => setProcId(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="proc-chain"
                className="block text-brand-text mb-1"
              >
                Blockchain Target Network
              </label>
              <select
                id="proc-chain"
                value={procChain}
                onChange={(e) => setProcChain(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent cursor-pointer"
              >
                <option value="bsc">BSC BEP-20</option>
                <option value="polygon">Polygon POS</option>
                <option value="base">Base Mainnet</option>
                <option value="avalanche">Avalanche C-Chain</option>
              </select>
            </div>

            <button
              id="run-process"
              type="submit"
              disabled={procLoading}
              className="w-full rounded-lg bg-zinc-900 py-2 font-semibold text-white hover:opacity-90 transition-opacity active:scale-[0.98] disabled:opacity-50 cursor-pointer"
            >
              {procLoading ? "Processing..." : "Simulate Handshake"}
            </button>
          </form>

          {procResult && (
            <div className="mt-3">
              <span className="text-[10px] font-bold text-brand-dim uppercase tracking-wider block mb-1">
                Process Diagnostics Console
              </span>
              <pre className="rounded bg-brand-bg px-3 py-2 font-mono text-[10px] text-brand-text overflow-x-auto max-h-48 border border-brand-border shadow-inner whitespace-pre-wrap select-all">
                {procResult}
              </pre>
            </div>
          )}
        </div>

        {/* Card 2: Sweep Address */}
        <div className="rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-brand-bg pb-3">
            <Settings className="h-4.5 w-4.5 text-zinc-950" />
            <span className="text-sm font-semibold text-brand-text">
              Active Chamber Sweep
            </span>
          </div>

          <form
            onSubmit={handleSweep}
            className="space-y-4 text-xs font-semibold"
          >
            <div>
              <label
                htmlFor="sweep-addr"
                className="block text-brand-text mb-1"
              >
                Vault Ethereum Address
              </label>
              <input
                id="sweep-addr"
                type="text"
                placeholder="0x742d35Cc6634C..."
                value={sweepAddr}
                onChange={(e) => setSweepAddr(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="sweep-chain"
                className="block text-brand-text mb-1"
              >
                Relayer Target Chain
              </label>
              <select
                id="sweep-chain"
                value={sweepChain}
                onChange={(e) => setSweepChain(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent cursor-pointer"
              >
                <option value="bsc">BSC BEP-20</option>
                <option value="polygon">Polygon POS</option>
                <option value="base">Base Mainnet</option>
                <option value="avalanche">Avalanche C-Chain</option>
              </select>
            </div>

            <button
              id="run-sweep"
              type="submit"
              disabled={sweepLoading}
              className="w-full rounded-lg bg-zinc-900 py-2 font-semibold text-white hover:opacity-90 transition-opacity active:scale-[0.98] disabled:opacity-50 cursor-pointer"
            >
              {sweepLoading ? "Sweeping..." : "Trigger Relayer Sweep"}
            </button>
          </form>

          {sweepResult && (
            <div className="mt-3">
              <span className="text-[10px] font-bold text-brand-dim uppercase tracking-wider block mb-1">
                Relayer Receipt Printout
              </span>
              <pre className="rounded bg-brand-bg px-3 py-2 font-mono text-[10px] text-brand-text overflow-x-auto max-h-48 border border-brand-border shadow-inner whitespace-pre-wrap select-all">
                {sweepResult}
              </pre>
            </div>
          )}
        </div>

        {/* Card 3: Send Webhook */}
        <div className="rounded-xl border border-brand-border bg-brand-surface p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b border-brand-bg pb-3">
            <BellRing className="h-4.5 w-4.5 text-zinc-950" />
            <span className="text-sm font-semibold text-brand-text">
              Simulated Webhook Pusher
            </span>
          </div>

          <form
            onSubmit={handleWebhook}
            className="space-y-4 text-xs font-semibold"
          >
            <div>
              <label htmlFor="wh-pid" className="block text-brand-text mb-1">
                Associated Payment UUID
              </label>
              <input
                id="wh-pid"
                type="text"
                placeholder="e.g. ad102e-f49c"
                value={whId}
                onChange={(e) => setWhId(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent transition-colors"
              />
            </div>

            <div>
              <label htmlFor="wh-ev" className="block text-brand-text mb-1">
                Dispatch Event Route
              </label>
              <select
                id="wh-ev"
                value={whEvent}
                onChange={(e) => setWhEvent(e.target.value)}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 focus:outline-none focus:border-brand-accent cursor-pointer"
              >
                <option value="payment.confirmed">payment.confirmed</option>
                <option value="payment.detected">payment.detected</option>
                <option value="payment.expired">payment.expired</option>
                <option value="payment.failed">payment.failed</option>
              </select>
            </div>

            <button
              id="run-webhook"
              type="submit"
              disabled={whLoading}
              className="w-full rounded-lg bg-zinc-900 py-2 font-semibold text-white hover:opacity-90 transition-opacity active:scale-[0.98] disabled:opacity-50 cursor-pointer"
            >
              {whLoading ? "Dispatching..." : "Dispatch Webhook Event"}
            </button>
          </form>

          {whResult && (
            <div className="mt-3">
              <span className="text-[10px] font-bold text-brand-dim uppercase tracking-wider block mb-1">
                Socket Dispatch Output logs
              </span>
              <pre className="rounded bg-brand-bg px-3 py-2 font-mono text-[10px] text-brand-text overflow-x-auto max-h-48 border border-brand-border shadow-inner whitespace-pre-wrap select-all">
                {whResult}
              </pre>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
