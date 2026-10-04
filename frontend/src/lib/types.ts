export type Mode = "FIRST_TIME" | "REBALANCE";
export type Side = "BUY" | "SELL";
export type ExecutionStatus = "RUNNING" | "COMPLETED" | "STOPPED";
export type OrderStatus = "QUEUED" | "PLACED" | "SUCCESS" | "PARTIAL" | "PENDING" | "FAILED" | "SKIPPED";

export interface Broker {
  broker: string;
  configured: boolean;
  connected: boolean;
  token_expires_at: string | null;
}

export interface ConnectResult {
  broker: string;
  connected?: boolean;
  login_url?: string;
}

export interface Order {
  sequence: number;
  symbol: string;
  side: Side;
  quantity: number;
  filled_quantity: number;
  status: OrderStatus;
  tag: string;
  broker_order_id: string;
  error_code: string;
  error_message: string;
  updated_at: string;
}

export interface Execution {
  id: string;
  mode: Mode;
  broker: string;
  status: ExecutionStatus;
  idempotency_key: string;
  error_message: string;
  created_at: string;
  finished_at: string | null;
  counts: Partial<Record<OrderStatus, number>>;
  orders: Order[];
}

export interface CreatedExecution {
  execution_id: string;
  status: ExecutionStatus;
}

export interface Sections {
  buy?: { symbol: string; quantity: number }[];
  sell?: { symbol: string; quantity: number }[];
  rebalance?: { symbol: string; quantity_change: number }[];
}
