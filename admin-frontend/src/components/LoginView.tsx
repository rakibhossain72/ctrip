import React, { useState } from "react";
import { motion } from "motion/react";
import { KeyRound } from "lucide-react";
import { login, setTokens } from "../api/auth";

interface LoginViewProps {
  onLogin: () => void;
  triggerToast: (msg: string, type?: "ok" | "err") => void;
}

export default function LoginView({ onLogin, triggerToast }: LoginViewProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim() || !password.trim()) {
      setErrorMsg("Please enter credentials");
      triggerToast("Credentials cannot be empty", "err");
      return;
    }

    setIsLoading(true);
    setErrorMsg("");

    try {
      const tokens = await login(username, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      onLogin();
      triggerToast("Signed in successfully", "ok");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setErrorMsg(msg);
      triggerToast(msg, "err");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      id="view-login"
      className="flex min-h-screen items-center justify-center p-4"
    >
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="w-full max-w-[380px]"
      >
        <div className="mb-8 text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand-accent text-xl font-bold text-white shadow-sm">
            C
          </div>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-brand-text">
            Ctrip Admin
          </h2>
          <p className="mt-1 text-sm text-brand-muted">
            Payment &amp; operations controller
          </p>
        </div>

        <div className="rounded-2xl border border-brand-border bg-brand-surface p-8 shadow-sm">
          {errorMsg && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-600">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="uname"
                className="block text-xs font-medium text-brand-text mb-1.5"
              >
                Username
              </label>
              <input
                id="uname"
                type="text"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  setErrorMsg("");
                }}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-sm text-brand-text placeholder-brand-dim focus:border-brand-accent focus:outline-none focus:ring-1 focus:ring-brand-accent transition-all"
                placeholder="Enter username"
                disabled={isLoading}
              />
            </div>

            <div>
              <label
                htmlFor="upass"
                className="block text-xs font-medium text-brand-text mb-1.5"
              >
                Password
              </label>
              <input
                id="upass"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setErrorMsg("");
                }}
                className="w-full rounded-lg border border-brand-border-dark bg-brand-surface px-3 py-2 text-sm text-brand-text placeholder-brand-dim focus:border-brand-accent focus:outline-none focus:ring-1 focus:ring-brand-accent transition-all"
                placeholder="Enter password"
                disabled={isLoading}
              />
            </div>

            <button
              id="submit-login"
              type="submit"
              disabled={isLoading}
              className="group flex w-full items-center justify-center gap-2 rounded-lg bg-brand-accent px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-brand-dim">
          Sign in to access the admin dashboard
        </p>
      </motion.div>
    </div>
  );
}