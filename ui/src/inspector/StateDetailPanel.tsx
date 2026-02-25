/**
 * StateDetailPanel - Shows input/output/error for the selected node.
 *
 * Features:
 * - Input/Output JSON display
 * - Error display for failed states
 * - Structural JSON diff between consecutive events when two events selected
 */

import { useMemo } from 'react';
import { useInspectStore } from '../store/inspectStore';
import { JsonDiff } from './JsonDiff';
import type { NodeOverlay } from './types';

function JsonBlock({ label, data }: { label: string; data: Record<string, unknown> | null }) {
  if (!data) return null;
  return (
    <div className="state-detail-section">
      <div className="state-detail-label">{label}</div>
      <pre className="state-detail-json">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export function StateDetailPanel() {
  const selectedNodeId = useInspectStore((s) => s.selectedNodeId);
  const snapshots = useInspectStore((s) => s.snapshots);
  const playbackIndex = useInspectStore((s) => s.playbackIndex);
  const executionDetail = useInspectStore((s) => s.executionDetail);

  // Get overlay data for the selected node from the current snapshot
  const overlay: NodeOverlay | null = useMemo(() => {
    if (!selectedNodeId || playbackIndex < 0 || playbackIndex >= snapshots.length)
      return null;
    return snapshots[playbackIndex].nodeOverlays[selectedNodeId] ?? null;
  }, [selectedNodeId, playbackIndex, snapshots]);

  // Get previous snapshot overlay for diff
  const prevOverlay: NodeOverlay | null = useMemo(() => {
    if (!selectedNodeId || playbackIndex <= 0 || playbackIndex >= snapshots.length)
      return null;
    return snapshots[playbackIndex - 1].nodeOverlays[selectedNodeId] ?? null;
  }, [selectedNodeId, playbackIndex, snapshots]);

  // Determine if we should show a diff (data changed between consecutive snapshots)
  const showDiff = useMemo(() => {
    if (!overlay || !prevOverlay) return false;
    const curr = overlay.output ?? overlay.input;
    const prev = prevOverlay.output ?? prevOverlay.input;
    if (!curr || !prev) return false;
    return JSON.stringify(curr) !== JSON.stringify(prev);
  }, [overlay, prevOverlay]);

  if (!executionDetail) {
    return (
      <div className="state-detail-panel">
        <div className="pane-header">State Detail</div>
        <div className="state-detail-empty">Select an execution</div>
      </div>
    );
  }

  if (!selectedNodeId || !overlay) {
    return (
      <div className="state-detail-panel">
        <div className="pane-header">State Detail</div>
        <div className="state-detail-empty">Click a node to inspect</div>
      </div>
    );
  }

  return (
    <div className="state-detail-panel">
      <div className="pane-header">State Detail: {selectedNodeId}</div>
      <div className="state-detail-content">
        <div className="state-detail-section">
          <div className="state-detail-label">Status</div>
          <div className="state-detail-value">{overlay.status}</div>
        </div>

        {overlay.durationMs !== null && (
          <div className="state-detail-section">
            <div className="state-detail-label">Duration</div>
            <div className="state-detail-value">
              {overlay.durationMs < 1000
                ? `${overlay.durationMs}ms`
                : `${(overlay.durationMs / 1000).toFixed(2)}s`}
            </div>
          </div>
        )}

        {overlay.retryAttempt > 0 && (
          <div className="state-detail-section">
            <div className="state-detail-label">Retry Attempt</div>
            <div className="state-detail-value">#{overlay.retryAttempt}</div>
          </div>
        )}

        <JsonBlock label="Input" data={overlay.input} />
        <JsonBlock label="Output" data={overlay.output} />

        {overlay.error && (
          <div className="state-detail-section">
            <div className="state-detail-label">Error</div>
            <pre className="state-detail-json state-detail-error">
              {overlay.error}
            </pre>
          </div>
        )}

        {showDiff && (
          <div className="state-detail-section">
            <div className="state-detail-label">Data Diff</div>
            <JsonDiff
              before={prevOverlay!.output ?? prevOverlay!.input ?? {}}
              after={overlay.output ?? overlay.input ?? {}}
            />
          </div>
        )}
      </div>
    </div>
  );
}
