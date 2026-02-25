import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function ParallelNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const branches = Array.isArray(stateData.Branches) ? stateData.Branches.length : 0;
  const hasRetry = Array.isArray(stateData.Retry) && stateData.Retry.length > 0;
  const hasCatch = Array.isArray(stateData.Catch) && stateData.Catch.length > 0;

  return (
    <BaseNode nodeProps={props} color="#3498db" icon="||">
      <div className="node-badges">
        <span className="badge badge-branches">{branches} branches</span>
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
      </div>
    </BaseNode>
  );
}
