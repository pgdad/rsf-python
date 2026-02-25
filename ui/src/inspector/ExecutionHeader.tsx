/**
 * ExecutionHeader - Shows metadata for the selected execution.
 *
 * Displays: name, status badge, start/end time, duration, execution ID.
 */

import { useInspectStore } from '../store/inspectStore';
import type { ExecutionStatus } from './types';

const STATUS_COLORS: Record<ExecutionStatus, string> = {
  RUNNING: '#3498db',
  SUCCEEDED: '#27ae60',
  FAILED: '#e74c3c',
  TIMED_OUT: '#e6a817',
  STOPPED: '#95a5a6',
};

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatDuration(startIso: string, endIso: string | null): string {
  if (!endIso) return 'In progress...';
  try {
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  } catch {
    return '--';
  }
}

export function ExecutionHeader() {
  const detail = useInspectStore((s) => s.executionDetail);
  if (!detail) return null;

  return (
    <div className="execution-header">
      <div className="execution-header-top">
        <span className="execution-header-name">
          {detail.name || detail.execution_id}
        </span>
        <span
          className="execution-header-status"
          style={{
            backgroundColor: STATUS_COLORS[detail.status] + '22',
            color: STATUS_COLORS[detail.status],
            borderColor: STATUS_COLORS[detail.status] + '44',
          }}
        >
          {detail.status}
        </span>
      </div>
      <div className="execution-header-meta">
        <span title="Start time">
          Started: {formatDateTime(detail.start_time)}
        </span>
        <span title="Duration">
          Duration: {formatDuration(detail.start_time, detail.end_time)}
        </span>
        <span className="execution-header-id" title={detail.execution_id}>
          ID: {detail.execution_id.slice(0, 16)}...
        </span>
      </div>
    </div>
  );
}
