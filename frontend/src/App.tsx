import { useEffect } from "react";
import { Toaster, toast } from "sonner";
import { LoginScreen } from "@/components/auth/login-screen";
import { useAuth } from "@/hooks/useAuth";
import { brokerName } from "@/lib/brokers";
import { Dashboard } from "@/pages/dashboard";

function useBrokerCallbackNotice() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const loginError = params.get("login_error");
    if (connected) toast.success(`${brokerName(connected)} connected`);
    if (loginError) toast.error(`Broker login failed: ${loginError}`);
    if (params.size) window.history.replaceState(null, "", window.location.pathname);
  }, []);
}

export function App() {
  const { token, login, logout } = useAuth();
  useBrokerCallbackNotice();

  return (
    <>
      {token ? <Dashboard onLogout={logout} /> : <LoginScreen onLogin={login} />}
      <Toaster position="bottom-right" richColors closeButton theme="system" />
    </>
  );
}
