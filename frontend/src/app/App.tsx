import { lazy, Suspense, type ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router';
import { PageLoader } from '@/components/ui';
import { landingPath, useAuth } from '@/lib/auth';

// Route-level code splitting: operators never download manager code (and its charts), and vice versa.
const OperatorApp = lazy(() => import('@/features/operator/OperatorApp'));
const ManagerApp = lazy(() => import('@/features/manager/ManagerApp'));
const LoginPage = lazy(() => import('@/features/auth/LoginPage'));

export function RequireAuth({ children, loginPath }: { children: ReactNode; loginPath: string }) {
  const { state } = useAuth();
  const location = useLocation();
  if (state.status === 'loading') return <PageLoader />;
  if (state.status === 'anon') return <Navigate to={loginPath} replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

function RootRedirect() {
  const { state } = useAuth();
  if (state.status === 'loading') return <PageLoader />;
  if (state.status === 'anon') return <Navigate to="/login" replace />;
  return <Navigate to={landingPath(state.user)} replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/floor/*" element={<OperatorApp />} />
          <Route path="/app/*" element={<ManagerApp />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
