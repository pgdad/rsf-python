import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function FailNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};

  return (
    <BaseNode nodeProps={props} color="#e74c3c" icon="&#10007;">
      {(stateData.Error != null || stateData.Cause != null) && (
        <div className="node-detail">
          {stateData.Error != null && (
            <div className="detail-line">Error: {String(stateData.Error)}</div>
          )}
          {stateData.Cause != null && (
            <div className="detail-line">Cause: {String(stateData.Cause)}</div>
          )}
        </div>
      )}
    </BaseNode>
  );
}
