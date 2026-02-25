/**
 * InspectorNode - Custom node component for the inspector graph.
 *
 * Renders node with status overlay (pending/running/succeeded/failed/caught),
 * timing info, and I/O indicator badges.
 */

import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { InspectNode } from '../store/inspectStore';
import type { NodeOverlay, NodeOverlayStatus } from './types';

const STATE_COLORS: Record<string, string> = {
  Task: '#4a90d9',
  Pass: '#7b68ee',
  Choice: '#e6a817',
  Wait: '#9b59b6',
  Succeed: '#27ae60',
  Fail: '#e74c3c',
  Parallel: '#3498db',
  Map: '#1abc9c',
};

const STATE_ICONS: Record<string, string> = {
  Task: 'T',
  Pass: 'P',
  Choice: '?',
  Wait: 'W',
  Succeed: '\u2713',
  Fail: '\u2717',
  Parallel: '\u2225',
  Map: 'M',
};

const STATUS_COLORS: Record<NodeOverlayStatus, string> = {
  pending: '#666666',
  running: '#3498db',
  succeeded: '#27ae60',
  failed: '#e74c3c',
  caught: '#e6a817',
};

const STATUS_LABELS: Record<NodeOverlayStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  succeeded: 'Succeeded',
  failed: 'Failed',
  caught: 'Caught',
};

function formatDuration(ms: number | null): string {
  if (ms === null) return '';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

export function InspectorNode(props: NodeProps<InspectNode>) {
  const { id, data, selected } = props;
  const stateType = data.stateType || 'Task';
  const color = STATE_COLORS[stateType] || '#4a90d9';
  const icon = STATE_ICONS[stateType] || '?';
  const overlay = data.overlay as NodeOverlay | undefined;

  const statusColor = overlay ? STATUS_COLORS[overlay.status] : '#666666';
  const borderColor = overlay ? statusColor : color;
  const isRunning = overlay?.status === 'running';

  return (
    <div
      className={`flow-node inspector-node ${selected ? 'selected' : ''} ${isRunning ? 'running-pulse' : ''}`}
      style={{ borderColor }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: color }}>
        <span className="node-icon">{icon}</span>
        <span className="node-type">{stateType}</span>
        {data.isStart && <span className="node-start-badge">START</span>}
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
        {overlay && (
          <div className="node-overlay-info">
            <div className="node-overlay-status" style={{ color: statusColor }}>
              <span
                className="status-dot"
                style={{ backgroundColor: statusColor }}
              />
              {STATUS_LABELS[overlay.status]}
            </div>
            {overlay.durationMs !== null && (
              <div className="node-overlay-timing">
                {formatDuration(overlay.durationMs)}
              </div>
            )}
            <div className="node-overlay-badges">
              {overlay.input && (
                <span className="badge badge-io">IN</span>
              )}
              {overlay.output && (
                <span className="badge badge-io">OUT</span>
              )}
              {overlay.error && (
                <span className="badge badge-catch">ERR</span>
              )}
              {overlay.retryAttempt > 0 && (
                <span className="badge badge-retry">
                  Retry #{overlay.retryAttempt}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
