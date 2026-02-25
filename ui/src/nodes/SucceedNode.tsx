import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { useFlowStore } from '../store/flowStore';

export function SucceedNode(props: NodeProps<FlowNode>) {
  const { id, data, selected } = props;
  const selectNode = useFlowStore((s) => s.selectNode);
  const hasErrors = data.errors && data.errors.length > 0;

  return (
    <div
      className={`flow-node terminal-node ${selected ? 'selected' : ''} ${hasErrors ? 'has-errors' : ''}`}
      style={{ borderColor: '#27ae60' }}
      onClick={() => selectNode(id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: '#27ae60' }}>
        <span className="node-icon">&#10003;</span>
        <span className="node-type">Succeed</span>
        {data.isStart && <span className="node-start-badge">START</span>}
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
      </div>
      {hasErrors && (
        <div className="node-error-badge" title={data.errors![0].message}>
          {data.errors!.length}
        </div>
      )}
    </div>
  );
}
