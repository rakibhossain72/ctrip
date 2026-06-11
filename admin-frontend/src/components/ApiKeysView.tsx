import { useState } from 'react';
import { fmtDate } from '../utils';
import { Key, Plus, Trash2, X, PlusCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useApiKeys } from '../api/queries';
import { useCreateApiKey, useRevokeApiKey } from '../api/mutations';

interface ApiKeysViewProps {
  triggerToast: (msg: string, type?: 'ok' | 'err') => void;
}

export default function ApiKeysView({ triggerToast }: ApiKeysViewProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [keyName, setKeyName] = useState('');
  const { data: keys = [], isLoading } = useApiKeys();
  const createKey = useCreateApiKey();
  const revokeKey = useRevokeApiKey();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = keyName.trim();
    if (!cleanName) {
      triggerToast('Key name cannot be empty', 'err');
      return;
    }

    try {
      await createKey.mutateAsync(cleanName);
      setKeyName('');
      setModalOpen(false);
      triggerToast('API Credentials Created successfully!', 'ok');
    } catch (err) {
      triggerToast(err instanceof Error ? err.message : 'Failed to create key', 'err');
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await revokeKey.mutateAsync(id);
      triggerToast('API Key revoked successfully', 'ok');
    } catch (err) {
      triggerToast(err instanceof Error ? err.message : 'Failed to revoke key', 'err');
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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-brand-text">API Credentials</h1>
          <p className="text-xs text-brand-muted">Authorize webhooks, integrations, and server queries safely.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 self-start rounded-lg bg-zinc-900 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:opacity-90 transition-transform active:scale-[0.98] cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          Create New Key
        </button>
      </div>

      <div className="rounded-xl border border-brand-border bg-brand-surface shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-brand-border bg-brand-bg/50 text-[11px] font-semibold tracking-wider text-brand-muted uppercase">
                <th className="px-5 py-3">Credential Name</th>
                <th className="px-5 py-3">Prefix Ident</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Created</th>
                <th className="px-5 py-3">Last Query</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border font-sans text-xs">
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-brand-bg/25 transition-colors">
                  <td className="px-5 py-4 font-semibold text-brand-text">{k.name}</td>
                  <td className="px-5 py-4">
                    <span className="font-mono text-xs rounded bg-brand-bg px-2 py-1 text-brand-muted border border-brand-border-dark select-all">
                      {k.key_prefix}…
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    {k.is_active ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700 border border-emerald-200">
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-bold text-zinc-500 border border-zinc-200 uppercase">
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-brand-muted">{fmtDate(new Date(k.created_at))}</td>
                  <td className="px-5 py-4 text-brand-muted">{k.last_used_at ? fmtDate(new Date(k.last_used_at)) : '—'}</td>
                  <td className="px-5 py-4 text-right">
                    {k.is_active ? (
                      <button
                        onClick={() => handleRevoke(k.id)}
                        className="inline-flex items-center gap-1 rounded-md border border-red-200 bg-red-50/50 px-2.5 py-1 text-[11px] font-semibold text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors cursor-pointer"
                      >
                        <Trash2 className="h-3 w-3" />
                        Revoke
                      </button>
                    ) : (
                      <span className="text-[11px] font-medium text-brand-dim uppercase tracking-wider pr-1">Terminated</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setModalOpen(false)}
              className="absolute inset-0 bg-zinc-900/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="relative w-full max-w-sm rounded-xl border border-brand-border bg-brand-surface p-6 shadow-xl"
            >
              <button
                onClick={() => setModalOpen(false)}
                className="absolute top-4 right-4 text-brand-muted hover:text-brand-text transition-colors cursor-pointer"
              >
                <X className="h-4.5 w-4.5" />
              </button>
              <div className="flex items-center gap-2 border-b border-brand-bg pb-3 mb-4">
                <Key className="h-5 w-5 text-zinc-800" />
                <h3 className="text-sm font-bold text-brand-text">Generate New API Key</h3>
              </div>
              <form onSubmit={handleCreate} className="space-y-4">
                <p className="text-xs text-brand-muted">Name the key according to its routing target.</p>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-brand-text">Key Identifier Name</label>
                  <input
                    type="text"
                    required
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    placeholder="e.g. Production Webhook System"
                    className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-xs text-brand-text focus:outline-none focus:border-brand-accent transition-colors"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="rounded-lg border border-brand-border-dark bg-white px-3.5 py-1.5 text-xs font-semibold text-brand-text hover:bg-brand-bg transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createKey.isPending}
                    className="inline-flex items-center gap-1 rounded-lg bg-zinc-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:opacity-90 transition-transform active:scale-[0.98] disabled:opacity-50 cursor-pointer"
                  >
                    <PlusCircle className="h-4 w-4" />
                    {createKey.isPending ? 'Creating...' : 'Create Key'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}