import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { useFlowStore } from '../store/flowStore';

export function FailNode(props: NodeProps<FlowNode>) {
  const { id, data, selected } = props;
  const selectNode = useFlowStore((s) => s.selectNode);
  const stateData = data.stateData || {};
  const hasErrors = data.errors && data.errors.length > 0;

  return (
    <div
      className={`flow-node terminal-node ${selected ? 'selected' : ''} ${hasErrors ? 'has-errors' : ''}`}
      style={{ borderColor: '#e74c3c' }}
      onClick={() => selectNode(id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: '#e74c3c' }}>
        <span className="node-icon">&#10007;</span>
        <span className="node-type">Fail</span>
        {data.isStart && <span className="node-start-badge">START</span>}
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
        {(stateData.Error != null || stateData.Cause != null) ? (
          <div className="node-detail">
            {stateData.Error != null && <div className="detail-line">Error: {String(stateData.Error)}</div>}
            {stateData.Cause != null && <div className="detail-line">Cause: {String(stateData.Cause)}</div>}
          </div>
        ) : null}
      </div>
      {hasErrors && (
        <div className="node-error-badge" title={data.errors![0].message}>
          {data.errors!.length}
        </div>
      )}
    </div>
  );
}
