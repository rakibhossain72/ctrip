import { Navigate, useNavigate, useLocation } from 'react-router-dom';
import LoginView from '../components/LoginView';

interface LoginPageProps {
  isLoggedIn: boolean;
  onLogin: () => void;
  triggerToast: (msg: string, type?: 'ok' | 'err') => void;
}

export default function LoginPage({ isLoggedIn, onLogin, triggerToast }: LoginPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from ?? '/overview';

  if (isLoggedIn) {
    return <Navigate to={from} replace />;
  }

  const handleLogin = () => {
    onLogin();
    navigate(from, { replace: true });
  };

  return <LoginView onLogin={handleLogin} triggerToast={triggerToast} />;
}