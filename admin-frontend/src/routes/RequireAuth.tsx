import { Navigate, useLocation, Outlet } from 'react-router-dom';

interface RequireAuthProps {
  isLoggedIn: boolean;
}

export default function RequireAuth({ isLoggedIn }: RequireAuthProps) {
  const location = useLocation();
  
  if (!isLoggedIn) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  
  return <Outlet />;
}