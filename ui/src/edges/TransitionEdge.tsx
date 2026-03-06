/**
 * Custom transition edge with support for normal, catch, default, and choice styles.
 * Supports visual selection highlight (blue stroke) via store selectedEdgeId.
 */

import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';
import type { FlowEdge } from '../types';
import { useFlowStore } from '../store/flowStore';

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

  const selectedEdgeId = useFlowStore((s) => s.selectedEdgeId);
  const isSelected = selectedEdgeId === id;

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

  // When selected, override to blue; otherwise use per-type color
  const strokeColor = isSelected
    ? '#3b82f6'
    : edgeType === 'catch'
      ? '#e74c3c'
      : edgeType === 'default'
        ? '#95a5a6'
        : edgeType === 'choice'
          ? '#e6a817'
          : '#555';

  const strokeWidth = isSelected ? 3 : 2;
  const strokeDasharray = !isSelected && edgeType === 'catch' ? '5 3' : undefined;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={isSelected ? 'selected' : undefined}
        interactionWidth={20}
        style={{
          stroke: strokeColor,
          strokeWidth,
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
              backgroundColor: isSelected
                ? '#3b82f6'
                : edgeType === 'catch'
                  ? '#fce4e4'
                  : '#f0f0f0',
              color: isSelected ? 'white' : strokeColor,
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
