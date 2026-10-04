import { getToken } from "./storage";
import type { Broker, ConnectResult, CreatedExecution, Execution } from "./types";

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<{ status: number; data: T }> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Token ${token}`;

  let response: Response;
  try {
    response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError("Cannot reach the server. Is it running?", 0);
  }

  const json = await response.json().catch(() => null);
  if (!response.ok || !json?.success) {
    if (response.status === 401 && token) onUnauthorized();
    throw new ApiError(json?.error ?? `Request failed (HTTP ${response.status})`, response.status, json?.details);
  }
  return { status: response.status, data: json.data as T };
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string }>("POST", "/api/auth/token/", { username, password }),
  brokers: () => request<Broker[]>("GET", "/api/brokers/"),
  connect: (broker: string) => request<ConnectResult>("GET", `/api/brokers/${encodeURIComponent(broker)}/login/`),
  createExecution: (payload: object) => request<CreatedExecution | Execution>("POST", "/api/executions/", payload),
  execution: (id: string) => request<Execution>("GET", `/api/executions/${encodeURIComponent(id)}/`),
};
