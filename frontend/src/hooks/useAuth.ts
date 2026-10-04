import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, setUnauthorizedHandler } from "@/lib/api";
import { getToken, setToken } from "@/lib/storage";

export function useAuth() {
  const [token, setTokenState] = useState<string | null>(getToken);

  const logout = useCallback(() => {
    setToken(null);
    setTokenState(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
      toast.error("Your session expired. Please sign in again.");
    });
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await api.login(username, password);
    setToken(data.token);
    setTokenState(data.token);
  }, []);

  return { token, login, logout };
}
