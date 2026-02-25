/**
 * TypeScript type definitions for the RSF Execution Inspector.
 */

/** Execution status from the backend */
export type ExecutionStatus =
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'TIMED_OUT'
  | 'STOPPED';

/** Terminal statuses (execution finished) */
export const TERMINAL_STATUSES: ReadonlySet<ExecutionStatus> = new Set([
  'SUCCEEDED',
  'FAILED',
  'TIMED_OUT',
  'STOPPED',
]);

/** Execution summary for list view */
export interface ExecutionSummary {
  execution_id: string;
  name: string;
  status: ExecutionStatus;
  function_name: string;
  start_time: string;
  end_time: string | null;
}

/** Error info for failed executions */
export interface ExecutionError {
  error: string;
  cause: string;
}

/** Full execution detail */
export interface ExecutionDetail {
  execution_id: string;
  name: string;
  status: ExecutionStatus;
  function_name: string;
  start_time: string;
  end_time: string | null;
  input_payload: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error: ExecutionError | null;
  history: HistoryEvent[];
}

/** A single history event */
export interface HistoryEvent {
  event_id: number;
  timestamp: string;
  event_type: string;
  sub_type: string | null;
  details: Record<string, unknown>;
}

/** Execution list response with pagination */
export interface ExecutionListResponse {
  executions: ExecutionSummary[];
  next_token: string | null;
}

/** Node overlay status for the inspector graph */
export type NodeOverlayStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'caught';

/** Overlay data for a single node in the inspector graph */
export interface NodeOverlay {
  status: NodeOverlayStatus;
  enteredAt: string | null;
  exitedAt: string | null;
  durationMs: number | null;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error: string | null;
  retryAttempt: number;
}

/** Overlay data for a single edge in the inspector graph */
export interface EdgeOverlay {
  traversed: boolean;
  timestamp: string | null;
}

/** A precomputed snapshot of the graph state at a specific point in time */
export interface TransitionSnapshot {
  eventIndex: number;
  timestamp: string;
  nodeOverlays: Record<string, NodeOverlay>;
  edgeOverlays: Record<string, EdgeOverlay>;
}

/** Status filter options for execution list */
export type StatusFilter = ExecutionStatus | 'ALL';
