import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function TaskNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const hasRetry = Array.isArray(stateData.Retry) && stateData.Retry.length > 0;
  const hasCatch = Array.isArray(stateData.Catch) && stateData.Catch.length > 0;
  const timeout = stateData.TimeoutSeconds as number | undefined;

  return (
    <BaseNode nodeProps={props} color="#4a90d9" icon="T">
      <div className="node-badges">
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
        {timeout && <span className="badge badge-timeout">{timeout}s</span>}
      </div>
    </BaseNode>
  );
}
