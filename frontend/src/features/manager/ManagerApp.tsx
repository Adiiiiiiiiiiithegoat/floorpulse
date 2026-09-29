import { Navigate, Route, Routes } from 'react-router';
import { RequireAuth } from '@/app/App';
import { useAuth } from '@/lib/auth';
import { ManagerShell } from './ManagerShell';
import { Dashboard } from './Dashboard';
import { Account } from './Account';

function OperatorsGoToFloor({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user && user.roles.every((r) => r === 'operator')) return <Navigate to="/floor" replace />;
  return <>{children}</>;
}

export default function ManagerApp() {
  return (
    <RequireAuth loginPath="/login">
      <OperatorsGoToFloor>
        <Routes>
          <Route element={<ManagerShell />}>
            <Route index element={<Dashboard />} />
            <Route path="account" element={<Account />} />
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Route>
        </Routes>
      </OperatorsGoToFloor>
    </RequireAuth>
  );
}
