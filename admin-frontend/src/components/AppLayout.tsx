import React from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import {
  LayoutDashboard,
  CreditCard,
  BarChart3,
  Key,
  Sliders,
  LogOut,
  X,
  Menu,
} from 'lucide-react';

const navItems = [
  { id: 'overview', label: 'Dashboard', icon: LayoutDashboard, to: '/overview' },
  { id: 'payments', label: 'Payments', icon: CreditCard, to: '/payments' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, to: '/analytics' },
  { id: 'apikeys', label: 'API Keys', icon: Key, to: '/apikeys' },
  { id: 'ops', label: 'Operations', icon: Sliders, to: '/ops' },
] as const;

type RouteId = (typeof navItems)[number]['id'];

const activeNavClass = (isActive: boolean) =>
  `flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-xs font-semibold transition-all cursor-pointer ${isActive ? 'bg-brand-bg text-brand-text font-bold' : 'text-brand-muted hover:bg-brand-bg/40 hover:text-brand-text'
  }`;

interface AppLayoutProps {
  handleLogout: () => void;
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
}

export default function AppLayout({
  handleLogout,
  isMobileMenuOpen,
  setIsMobileMenuOpen,
}: AppLayoutProps) {
  const location = useLocation();
  const currentSection = location.pathname.startsWith('/payments') ? 'payments' : (location.pathname.slice(1) as RouteId) || 'overview';
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-brand-bg font-sans selection:bg-brand-accent selection:text-white">
      {/* Mobile Drawer Backdrop */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsMobileMenuOpen(false)}
            className="fixed inset-0 z-40 bg-zinc-950/40 backdrop-blur-sm sm:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar Navigation */}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-brand-border bg-brand-surface transition-transform duration-300 ease-in-out sm:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        } sm:flex`}>
        <div className="flex h-14 items-center justify-between border-b border-brand-border px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7.5 w-7.5 items-center justify-center rounded bg-brand-accent font-sans text-sm font-bold text-white shadow-sm">
              C
            </div>
            <div>
              <span className="font-semibold text-sm tracking-tight text-brand-text">Ctrip Core</span>
              <p className="text-[10px] text-brand-dim font-bold tracking-widest uppercase">
                Admin Controller
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsMobileMenuOpen(false)}
            className="rounded-md p-1.5 text-brand-dim hover:bg-brand-bg hover:text-brand-text cursor-pointer sm:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-7 px-3 py-6">
          <div className="space-y-1">
            <span className="px-3.5 text-[9px] font-bold text-brand-dim uppercase tracking-widest">
              Overview Context
            </span>
            <div className="pt-2 space-y-1">
              {navItems.slice(0, 3).map((item) => {
                const IconComp = item.icon;
                return (
                  <NavLink key={item.id} to={item.to} className={({ isActive }) => activeNavClass(isActive)}>
                    <IconComp className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>

          <div className="space-y-1">
            <span className="px-3.5 text-[9px] font-bold text-brand-dim uppercase tracking-widest">
              System Operations
            </span>
            <div className="pt-2 space-y-1">
              {navItems.slice(3).map((item) => {
                const IconComp = item.icon;
                return (
                  <NavLink key={item.id} to={item.to} className={({ isActive }) => activeNavClass(isActive)}>
                    <IconComp className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>
        </nav>

        <div className="border-t border-brand-border p-3">
          <button
            onClick={() => {
              handleLogout();
              navigate('/login');
              setIsMobileMenuOpen(false);
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-xs font-semibold text-brand-muted hover:bg-red-50 hover:text-red-700 transition-all cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            Sign Out Session
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col sm:pl-60">
        <header className="sticky top-0 z-25 flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface/80 backdrop-blur-md px-6 shadow-sm select-none">
          <div className="flex items-center gap-3 sm:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="rounded-lg p-1.5 text-brand-muted hover:bg-brand-bg hover:text-brand-text cursor-pointer active:scale-95 transition-transform"
              title="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex h-7 w-7 items-center justify-center rounded bg-brand-accent text-xs font-bold text-white">
              C
            </div>
            <span className="font-bold text-xs tracking-tight text-zinc-800">Ctrip Admin</span>
          </div>

          <span className="text-xs font-semibold text-brand-muted hidden sm:inline">
            Ctrip Operations Ledger / Console System
          </span>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="block text-[11px] font-bold text-brand-text">Operator</span>
              <span className="block text-[10px] text-brand-dim leading-none font-mono font-medium">
                admin
              </span>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-brand-border bg-brand-bg text-xs font-bold text-zinc-700 uppercase">
              A
            </div>
          </div>
        </header>

        {/* Mobile Tabbar */}
        <nav className="flex justify-around border-t border-b border-brand-border bg-white px-2 py-1.5 sm:hidden">
          {navItems.map((item) => {
            const IconComp = item.icon;
            const isActive = item.id === currentSection;
            return (
              <NavLink
                key={item.id}
                to={item.to}
                className={({ isActive }) => `flex flex-col items-center gap-1 rounded px-2 py-0.5 text-[9px] font-semibold tracking-wide ${isActive ? 'text-zinc-950 font-bold' : 'text-brand-dim'}`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                <IconComp className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Dynamic Nested Content */}
        <main className="flex-1 p-4 sm:p-6 md:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
