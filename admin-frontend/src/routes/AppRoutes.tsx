import { Routes, Navigate, useNavigate, Route } from 'react-router-dom';
import RequireAuth from './RequireAuth';
import LoginPage from './LoginPage';
import PaymentDetailRoute from './PaymentDetailRoute';
import AppLayout from '../components/AppLayout';
import DashboardView from '../components/DashboardView';
import PaymentsView from '../components/PaymentsView';
import AnalyticsView from '../components/AnalyticsView';
import ApiKeysView from '../components/ApiKeysView';
import OperationsView from '../components/OperationsView';
import { useDashboardSummary, usePayments, useApiKeys } from '../api/queries';

interface AppRoutesProps {
  isLoggedIn: boolean;
  onLogin: () => void;
  onLogout: () => void;
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  triggerToast: (msg: string, type?: 'ok' | 'err') => void;
}

export default function AppRoutes({
  isLoggedIn,
  onLogin,
  onLogout,
  isMobileMenuOpen,
  setIsMobileMenuOpen,
  triggerToast,
}: AppRoutesProps) {
  const navigate = useNavigate();
  const { data: dashboard } = useDashboardSummary();
  const { data: payments = [] } = usePayments();
  const { data: apiKeys = [] } = useApiKeys();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <LoginPage isLoggedIn={isLoggedIn} onLogin={onLogin} triggerToast={triggerToast} />
        }
      />
      <Route element={<RequireAuth isLoggedIn={isLoggedIn} />}>
        <Route
          element={
            <AppLayout
              handleLogout={onLogout}
              isMobileMenuOpen={isMobileMenuOpen}
              setIsMobileMenuOpen={setIsMobileMenuOpen}
            />
          }
        >
          <Route
            index
            element={
              <DashboardView
                onSelectPayment={(id) => navigate(`/payments/${id}`)}
                onNavigateToPayments={() => navigate('/payments')}
              />
            }
          />
          <Route
            path="overview"
            element={
              <DashboardView
                onSelectPayment={(id) => navigate(`/payments/${id}`)}
                onNavigateToPayments={() => navigate('/payments')}
              />
            }
          />
          <Route
            path="payments"
            element={
              <PaymentsView
                onSelectPayment={(id) => navigate(`/payments/${id}`)}
              />
            }
          />
          <Route path="payments/:paymentId" element={<PaymentDetailRoute triggerToast={triggerToast} />} />
          <Route path="analytics" element={<AnalyticsView />} />
          <Route
            path="apikeys"
            element={
              <ApiKeysView
                triggerToast={triggerToast}
              />
            }
          />
          <Route path="ops" element={<OperationsView triggerToast={triggerToast} />} />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Route>
      </Route>
      <Route
        path="*"
        element={<Navigate to={isLoggedIn ? '/overview' : '/login'} replace />}
      />
    </Routes>
  );
}