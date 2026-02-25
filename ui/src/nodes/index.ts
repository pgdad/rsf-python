export { TaskNode } from './TaskNode';
export { PassNode } from './PassNode';
export { ChoiceNode } from './ChoiceNode';
export { WaitNode } from './WaitNode';
export { SucceedNode } from './SucceedNode';
export { FailNode } from './FailNode';
export { ParallelNode } from './ParallelNode';
export { MapNode } from './MapNode';

import type { NodeTypes } from '@xyflow/react';
import { TaskNode } from './TaskNode';
import { PassNode } from './PassNode';
import { ChoiceNode } from './ChoiceNode';
import { WaitNode } from './WaitNode';
import { SucceedNode } from './SucceedNode';
import { FailNode } from './FailNode';
import { ParallelNode } from './ParallelNode';
import { MapNode } from './MapNode';

/** Map of state type to React component for @xyflow/react */
export const nodeTypes: NodeTypes = {
  Task: TaskNode,
  Pass: PassNode,
  Choice: ChoiceNode,
  Wait: WaitNode,
  Succeed: SucceedNode,
  Fail: FailNode,
  Parallel: ParallelNode,
  Map: MapNode,
} as NodeTypes;
