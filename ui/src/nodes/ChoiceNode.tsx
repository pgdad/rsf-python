import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function ChoiceNode(props: NodeProps<FlowNode>) {
  const stateData = props.data.stateData || {};
  const choices = Array.isArray(stateData.Choices) ? stateData.Choices.length : 0;
  const hasDefault = stateData.Default !== undefined;

  return (
    <BaseNode nodeProps={props} color="#e6a817" icon="?">
      <div className="node-badges">
        <span className="badge badge-rules">{choices} rules</span>
        {hasDefault && <span className="badge badge-default">Default</span>}
      </div>
    </BaseNode>
  );
}
