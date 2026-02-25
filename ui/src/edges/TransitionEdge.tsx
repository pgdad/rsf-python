/**
 * Custom transition edge with support for normal, catch, default, and choice styles.
 */

import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import type { FlowEdge } from '../types';

export function TransitionEdge(props: EdgeProps<FlowEdge>) {
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

  const edgeType = data?.edgeType ?? 'normal';
  const label = data?.label;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const strokeColor =
    edgeType === 'catch'
      ? '#e74c3c'
      : edgeType === 'default'
        ? '#95a5a6'
        : edgeType === 'choice'
          ? '#e6a817'
          : '#555';

  const strokeDasharray = edgeType === 'catch' ? '5 3' : undefined;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: strokeColor,
          strokeWidth: 2,
          strokeDasharray,
        }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="edge-label"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              backgroundColor: edgeType === 'catch' ? '#fce4e4' : '#f0f0f0',
              color: strokeColor,
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '10px',
              fontWeight: 600,
              pointerEvents: 'all',
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
