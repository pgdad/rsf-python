/**
 * ReplayModal - Modal dialog for replaying an execution with editable payload.
 *
 * Features:
 * - Pre-fills textarea with original execution's input_payload
 * - JSON syntax validation — Execute button disabled until valid
 * - On success: closes modal, selects new execution (SSE auto-connects)
 * - On failure: shows error in modal, keeps it open for retry
 */

import { useState, useEffect } from 'react';
import { useInspectStore } from '../store/inspectStore';
import type { ReplayResponse } from './types';

export function ReplayModal() {
  const detail = useInspectStore((s) => s.executionDetail);
  const isOpen = useInspectStore((s) => s.replayModalOpen);
  const loading = useInspectStore((s) => s.replayLoading);
  const error = useInspectStore((s) => s.replayError);
  const closeReplayModal = useInspectStore((s) => s.closeReplayModal);
  const setReplayLoading = useInspectStore((s) => s.setReplayLoading);
  const setReplayError = useInspectStore((s) => s.setReplayError);
  const selectExecution = useInspectStore((s) => s.selectExecution);
  const addReplayedId = useInspectStore((s) => s.addReplayedId);

  const [payloadText, setPayloadText] = useState('');
  const [jsonValid, setJsonValid] = useState(true);

  // Pre-fill with original payload when modal opens
  useEffect(() => {
    if (isOpen && detail) {
      const text = detail.input_payload
        ? JSON.stringify(detail.input_payload, null, 2)
        : '{}';
      setPayloadText(text);
      setJsonValid(true);
    }
  }, [isOpen, detail]);

  // Validate JSON on change
  useEffect(() => {
    try {
      JSON.parse(payloadText);
      setJsonValid(true);
    } catch {
      setJsonValid(false);
    }
  }, [payloadText]);

  if (!isOpen || !detail) return null;

  const handleExecute = async () => {
    setReplayLoading(true);
    setReplayError(null);

    try {
      const payload = JSON.parse(payloadText);
      const resp = await fetch(
        `/api/inspect/execution/${encodeURIComponent(detail.execution_id)}/replay`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ input_payload: payload }),
        },
      );

      if (!resp.ok) {
        const errData = await resp
          .json()
          .catch(() => ({ detail: resp.statusText }));
        throw new Error(
          errData.detail || `Replay failed: ${resp.status}`,
        );
      }

      const data: ReplayResponse = await resp.json();
      closeReplayModal();
      // Track replayed execution for badge display
      addReplayedId(data.execution_id);
      // Select the new execution — SSE auto-connects via existing useSSE
      selectExecution(data.execution_id);
    } catch (err) {
      setReplayError(
        err instanceof Error ? err.message : 'Replay failed',
      );
    } finally {
      setReplayLoading(false);
    }
  };

  return (
    <div className="replay-modal-overlay" onClick={closeReplayModal}>
      <div className="replay-modal" onClick={(e) => e.stopPropagation()}>
        <div className="replay-modal-header">
          <h3>Replay Execution</h3>
          <button
            className="replay-modal-close"
            onClick={closeReplayModal}
          >
            &times;
          </button>
        </div>
        <div className="replay-modal-body">
          <label className="replay-payload-label">
            Input Payload (JSON):
          </label>
          <textarea
            className={`replay-payload-editor ${!jsonValid ? 'invalid' : ''}`}
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
            rows={12}
            spellCheck={false}
          />
          {!jsonValid && (
            <div className="replay-error">Invalid JSON syntax</div>
          )}
          {error && <div className="replay-error">{error}</div>}
        </div>
        <div className="replay-modal-footer">
          <button
            className="replay-cancel-btn"
            onClick={closeReplayModal}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            className="replay-execute-btn"
            onClick={handleExecute}
            disabled={!jsonValid || loading}
          >
            {loading ? 'Executing...' : 'Execute'}
          </button>
        </div>
      </div>
    </div>
  );
}
