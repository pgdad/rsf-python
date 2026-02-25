import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function MapNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const maxConcurrency = stateData.MaxConcurrency as number | undefined;
  const hasRetry = Array.isArray(stateData.Retry) && stateData.Retry.length > 0;
  const hasCatch = Array.isArray(stateData.Catch) && stateData.Catch.length > 0;

  return (
    <BaseNode nodeProps={props} color="#1abc9c" icon="M">
      <div className="node-badges">
        {maxConcurrency !== undefined && (
          <span className="badge badge-concurrency">max: {maxConcurrency}</span>
        )}
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
      </div>
    </BaseNode>
  );
}
