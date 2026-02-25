/**
 * Base node component shared by all state type nodes.
 * Provides consistent layout with handles, label, and type badge.
 */

import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { useFlowStore } from '../store/flowStore';

interface BaseNodeProps {
  nodeProps: NodeProps<FlowNode>;
  color: string;
  icon: string;
  children?: React.ReactNode;
}

export function BaseNode({ nodeProps, color, icon, children }: BaseNodeProps) {
  const { id, data, selected } = nodeProps;
  const selectNode = useFlowStore((s) => s.selectNode);
  const hasErrors = data.errors && data.errors.length > 0;

  return (
    <div
      className={`flow-node ${selected ? 'selected' : ''} ${hasErrors ? 'has-errors' : ''}`}
      style={{ borderColor: color }}
      onClick={() => selectNode(id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: color }}>
        <span className="node-icon">{icon}</span>
        <span className="node-type">{data.stateType}</span>
        {data.isStart && <span className="node-start-badge">START</span>}
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
        {children}
      </div>
      {hasErrors && (
        <div className="node-error-badge" title={data.errors![0].message}>
          {data.errors!.length}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
