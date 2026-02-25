/**
 * InspectorEdge - Custom edge for the inspector graph with traversal overlay.
 *
 * Shows whether the edge was traversed and at what time.
 */

import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import type { InspectEdge } from '../store/inspectStore';
import type { EdgeOverlay } from './types';

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
}

export function InspectorEdge(props: EdgeProps<InspectEdge>) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    markerEnd,
  } = props;

  const overlay = data?.overlay as EdgeOverlay | undefined;
  const edgeType = data?.edgeType ?? 'normal';

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  // Base color by edge type
  let strokeColor = '#555';
  if (edgeType === 'catch') strokeColor = '#e74c3c';
  else if (edgeType === 'default') strokeColor = '#95a5a6';
  else if (edgeType === 'choice') strokeColor = '#e6a817';

  // Override with overlay traversal state
  const traversed = overlay?.traversed ?? false;
  if (traversed) {
    strokeColor = '#27ae60';
  }

  const strokeDasharray = edgeType === 'catch' ? '5 3' : undefined;
  const opacity = traversed ? 1.0 : 0.35;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: strokeColor,
          strokeWidth: traversed ? 3 : 2,
          strokeDasharray,
          opacity,
          transition: 'stroke 0.3s, stroke-width 0.3s, opacity 0.3s',
        }}
      />
      {traversed && overlay?.timestamp && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              backgroundColor: '#27ae6022',
              color: '#27ae60',
              border: '1px solid #27ae6044',
              padding: '1px 5px',
              borderRadius: '3px',
              fontSize: '9px',
              fontWeight: 600,
              pointerEvents: 'all',
            }}
          >
            {formatTime(overlay.timestamp)}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
