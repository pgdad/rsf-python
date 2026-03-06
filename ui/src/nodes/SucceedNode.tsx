import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';

export function SucceedNode(props: NodeProps<FlowNode>) {
  return (
    <BaseNode nodeProps={props} color="#27ae60" icon="&#10003;" />
  );
}
