/**
 * SSE connection hook for live execution updates.
 *
 * Manages EventSource lifecycle: connect, receive events, auto-close
 * on terminal status, and pause when the browser tab is hidden.
 */

import { useEffect, useRef, useCallback } from 'react';
import type { ExecutionDetail, HistoryEvent } from './types';
import { TERMINAL_STATUSES } from './types';

interface UseSSEOptions {
  executionId: string | null;
  baseUrl?: string;
  onExecutionInfo: (detail: Omit<ExecutionDetail, 'history'>) => void;
  onHistory: (events: HistoryEvent[]) => void;
  onHistoryUpdate: (events: HistoryEvent[]) => void;
  onError?: (error: Event) => void;
}

export function useSSE({
  executionId,
  baseUrl = '',
  onExecutionInfo,
  onHistory,
  onHistoryUpdate,
  onError,
}: UseSSEOptions) {
  const sourceRef = useRef<EventSource | null>(null);
  const pausedRef = useRef(false);

  const close = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!executionId) {
      close();
      return;
    }

    const url = `${baseUrl}/api/inspect/execution/${encodeURIComponent(executionId)}/stream`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.addEventListener('execution_info', (e: MessageEvent) => {
      if (pausedRef.current) return;
      const data = JSON.parse(e.data) as Omit<ExecutionDetail, 'history'>;
      onExecutionInfo(data);

      // Auto-close on terminal status
      if (TERMINAL_STATUSES.has(data.status)) {
        // Give a moment for any final history_update events
        setTimeout(() => close(), 500);
      }
    });

    source.addEventListener('history', (e: MessageEvent) => {
      if (pausedRef.current) return;
      const events = JSON.parse(e.data) as HistoryEvent[];
      onHistory(events);
    });

    source.addEventListener('history_update', (e: MessageEvent) => {
      if (pausedRef.current) return;
      const events = JSON.parse(e.data) as HistoryEvent[];
      onHistoryUpdate(events);
    });

    source.onerror = (e) => {
      onError?.(e);
    };

    // Pause when tab is hidden, resume when visible
    const handleVisibility = () => {
      pausedRef.current = document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      close();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [executionId, baseUrl, onExecutionInfo, onHistory, onHistoryUpdate, onError, close]);

  return { close };
}
