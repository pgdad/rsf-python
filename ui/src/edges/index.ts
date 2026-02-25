export { TransitionEdge } from './TransitionEdge';

import type { EdgeTypes } from '@xyflow/react';
import { TransitionEdge } from './TransitionEdge';

export const edgeTypes: EdgeTypes = {
  transition: TransitionEdge,
} as EdgeTypes;
