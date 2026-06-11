import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { HashRouter } from 'react-router-dom';
import { AlertTriangle, CheckCircle, X } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppRoutes } from './routes';
import { ToastMessage } from './types';
import { getAccessToken, getApiKey } from './api/auth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function hasAuthToken(): boolean {
  return !!(getAccessToken() || getApiKey());
}

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(hasAuthToken);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const triggerToast = (message: string, type: 'ok' | 'err' = 'ok') => {
    const id = Date.now().toString() + Math.random().toString();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4500);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleLogin = () => setIsLoggedIn(true);

  const handleLogout = () => {
    setIsLoggedIn(false);
    queryClient.clear();
    triggerToast('Logged out of system administrator session', 'ok');
  };

  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <AppRoutes
          isLoggedIn={isLoggedIn}
          onLogin={handleLogin}
          onLogout={handleLogout}
          isMobileMenuOpen={isMobileMenuOpen}
          setIsMobileMenuOpen={setIsMobileMenuOpen}
          triggerToast={triggerToast}
        />

        <div id="toasts-portal" className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-[320px]">
          <AnimatePresence>
            {toasts.map((toast) => (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, x: 50, scale: 0.9 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 50, scale: 0.9 }}
                className={`flex gap-3 items-start rounded-lg border p-4 shadow-md bg-white ${
                  toast.type === 'err' ? 'border-red-200' : 'border-emerald-200'
                }`}
              >
                {toast.type === 'err' ? (
                  <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className="text-xs font-semibold text-brand-text leading-tight">
                    {toast.message}
                  </p>
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  className="text-brand-dim hover:text-brand-text transition-colors cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </HashRouter>
    </QueryClientProvider>
  );
}