import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errorMessage } from "@/lib/api";
import { brokerName } from "@/lib/brokers";
import type { Broker } from "@/lib/types";

export function useBrokers() {
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.brokers();
      setBrokers(data);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const connect = useCallback(
    async (broker: string) => {
      setConnecting(broker);
      try {
        const { data } = await api.connect(broker);
        if (data.login_url) {
          window.location.assign(data.login_url);
          return;
        }
        toast.success(`${brokerName(broker)} connected`);
        await refresh();
      } catch (error) {
        toast.error(errorMessage(error));
      } finally {
        setConnecting(null);
      }
    },
    [refresh],
  );

  return { brokers, loading, connecting, connect };
}
