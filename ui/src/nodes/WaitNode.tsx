import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function WaitNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const seconds = stateData.Seconds as number | undefined;
  const timestamp = stateData.Timestamp as string | undefined;

  let waitDisplay = '';
  if (seconds !== undefined) waitDisplay = `${seconds}s`;
  else if (timestamp) waitDisplay = timestamp;
  else if (stateData.SecondsPath) waitDisplay = 'Path';
  else if (stateData.TimestampPath) waitDisplay = 'Path';

  return (
    <BaseNode nodeProps={props} color="#9b59b6" icon="W">
      {waitDisplay && (
        <div className="node-badges">
          <span className="badge badge-wait">{waitDisplay}</span>
        </div>
      )}
    </BaseNode>
  );
}
