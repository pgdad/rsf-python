import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function PassNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const hasResult = stateData.Result !== undefined;

  return (
    <BaseNode nodeProps={props} color="#7b68ee" icon="P">
      {hasResult && (
        <div className="node-badges">
          <span className="badge badge-result">Result</span>
        </div>
      )}
    </BaseNode>
  );
}
