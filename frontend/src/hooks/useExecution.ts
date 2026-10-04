import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiError, api, errorMessage } from "@/lib/api";
import type { Execution } from "@/lib/types";

const POLL_MS = 2000;

export function useExecution() {
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [execution, setExecution] = useState<Execution | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    if (!executionId) return;
    let cancelled = false;
    let warned = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const { data } = await api.execution(executionId);
        if (cancelled) return;
        setExecution(data);
        if (data.status === "RUNNING") timer = setTimeout(poll, POLL_MS);
      } catch (error) {
        if (cancelled) return;
        const retryable = !(error instanceof ApiError) || error.status === 0 || error.status >= 500;
        if (!warned) toast.error(retryable ? `${errorMessage(error)} Retrying...` : errorMessage(error));
        warned = true;
        if (retryable) timer = setTimeout(poll, POLL_MS);
        else setStopped(true);
      }
    };

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [executionId]);

  const submit = useCallback(async (payload: object) => {
    setSubmitting(true);
    try {
      const { data } = await api.createExecution(payload);
      const id = "execution_id" in data ? data.execution_id : data.id;
      setExecution(null);
      setStopped(false);
      setExecutionId(id);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }, []);

  const waiting = executionId !== null && !stopped && (execution === null || execution.status === "RUNNING");

  return { execution, running: submitting || waiting, submit };
}
