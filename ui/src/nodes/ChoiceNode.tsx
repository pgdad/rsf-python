import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { useFlowStore } from '../store/flowStore';

export function ChoiceNode(props: NodeProps<FlowNode>) {
  const { id, data, selected } = props;
  const selectNode = useFlowStore((s) => s.selectNode);
  const stateData = data.stateData || {};
  const choices = Array.isArray(stateData.Choices) ? stateData.Choices.length : 0;
  const hasDefault = stateData.Default !== undefined;
  const hasErrors = data.errors && data.errors.length > 0;

  return (
    <div
      className={`flow-node choice-node ${selected ? 'selected' : ''} ${hasErrors ? 'has-errors' : ''}`}
      style={{ borderColor: '#e6a817' }}
      onClick={() => selectNode(id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: '#e6a817' }}>
        <span className="node-icon">?</span>
        <span className="node-type">Choice</span>
        {data.isStart && <span className="node-start-badge">START</span>}
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
        <div className="node-badges">
          <span className="badge badge-rules">{choices} rules</span>
          {hasDefault && <span className="badge badge-default">Default</span>}
        </div>
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
