import { Navigate, useNavigate, useParams } from 'react-router-dom';
import PaymentDetailView from '../components/PaymentDetailView';

interface PaymentDetailRouteProps {
  triggerToast: (msg: string, type?: 'ok' | 'err') => void;
}

export default function PaymentDetailRoute({ triggerToast }: PaymentDetailRouteProps) {
  const { paymentId } = useParams<{ paymentId: string }>();
  const navigate = useNavigate();

  if (!paymentId) {
    return <Navigate to="/payments" replace />;
  }

  return (
    <PaymentDetailView
      paymentId={paymentId}
      onBack={() => navigate('/payments')}
      triggerToast={triggerToast}
    />
  );
}