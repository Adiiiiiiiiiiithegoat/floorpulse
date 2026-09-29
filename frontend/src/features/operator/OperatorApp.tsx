import { Route, Routes } from 'react-router';
import { RequireAuth } from '@/app/App';
import { useTheme } from '@/components/Prefs';
import { DeviceSetup } from './DeviceSetup';
import { PinLogin } from './PinLogin';
import { OperatorShell } from './OperatorShell';
import { FloorHome } from './FloorHome';

export default function OperatorApp() {
  const [theme, setTheme] = useTheme('floor');
  return (
    <Routes>
      <Route path="setup" element={<DeviceSetup />} />
      <Route path="login" element={<PinLogin />} />
      <Route
        element={
          <RequireAuth loginPath="/floor/login">
            <OperatorShell theme={theme} onTheme={setTheme} />
          </RequireAuth>
        }
      >
        <Route index element={<FloorHome />} />
      </Route>
    </Routes>
  );
}
