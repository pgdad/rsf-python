/**
 * ExecutionList - Left panel showing executions with filter and search.
 *
 * Features:
 * - Status filter dropdown (ALL, RUNNING, SUCCEEDED, FAILED, TIMED_OUT, STOPPED)
 * - Text search by execution name
 * - Color-coded status icons
 * - Click to select and stream execution
 */

import { useCallback, useEffect } from 'react';
import { useInspectStore } from '../store/inspectStore';
import type { ExecutionStatus, StatusFilter } from './types';

const STATUS_COLORS: Record<ExecutionStatus, string> = {
  RUNNING: '#3498db',
  SUCCEEDED: '#27ae60',
  FAILED: '#e74c3c',
  TIMED_OUT: '#e6a817',
  STOPPED: '#95a5a6',
};

const STATUS_ICONS: Record<ExecutionStatus, string> = {
  RUNNING: '\u25B6',
  SUCCEEDED: '\u2713',
  FAILED: '\u2717',
  TIMED_OUT: '\u231A',
  STOPPED: '\u25A0',
};

const FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'ALL', label: 'All Statuses' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'SUCCEEDED', label: 'Succeeded' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'TIMED_OUT', label: 'Timed Out' },
  { value: 'STOPPED', label: 'Stopped' },
];

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function ExecutionList() {
  const executions = useInspectStore((s) => s.executions);
  const statusFilter = useInspectStore((s) => s.statusFilter);
  const searchQuery = useInspectStore((s) => s.searchQuery);
  const selectedExecutionId = useInspectStore((s) => s.selectedExecutionId);
  const loading = useInspectStore((s) => s.loading);
  const setStatusFilter = useInspectStore((s) => s.setStatusFilter);
  const setSearchQuery = useInspectStore((s) => s.setSearchQuery);
  const setExecutions = useInspectStore((s) => s.setExecutions);
  const setLoading = useInspectStore((s) => s.setLoading);
  const selectExecution = useInspectStore((s) => s.selectExecution);

  const fetchExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'ALL') {
        params.set('status', statusFilter);
      }
      params.set('max_items', '50');
      const resp = await fetch(`/api/inspect/executions?${params}`);
      if (resp.ok) {
        const data = await resp.json();
        setExecutions(data.executions, data.next_token);
      }
    } catch (err) {
      console.error('Failed to fetch executions:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, setExecutions, setLoading]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  // Filter locally by search query
  const filtered = executions.filter((exec) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      exec.name.toLowerCase().includes(q) ||
      exec.execution_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="execution-list">
      <div className="pane-header">Executions</div>
      <div className="execution-list-controls">
        <select
          className="execution-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
        >
          {FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <input
          className="execution-search"
          type="text"
          placeholder="Search executions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          className="execution-refresh"
          onClick={fetchExecutions}
          disabled={loading}
          title="Refresh"
        >
          {loading ? '...' : '\u21BB'}
        </button>
      </div>
      <div className="execution-list-items">
        {filtered.length === 0 && !loading && (
          <div className="execution-list-empty">No executions found</div>
        )}
        {filtered.map((exec) => (
          <div
            key={exec.execution_id}
            className={`execution-list-item ${selectedExecutionId === exec.execution_id ? 'selected' : ''}`}
            onClick={() => selectExecution(exec.execution_id)}
          >
            <span
              className="execution-status-icon"
              style={{ color: STATUS_COLORS[exec.status] }}
              title={exec.status}
            >
              {STATUS_ICONS[exec.status]}
            </span>
            <div className="execution-item-info">
              <div className="execution-item-name">
                {exec.name || exec.execution_id}
              </div>
              <div className="execution-item-meta">
                <span className="execution-item-time">
                  {formatTime(exec.start_time)}
                </span>
                <span
                  className="execution-item-status"
                  style={{ color: STATUS_COLORS[exec.status] }}
                >
                  {exec.status}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
