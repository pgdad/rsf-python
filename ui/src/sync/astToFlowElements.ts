/**
 * Converts a parsed AST (from the backend) into @xyflow/react nodes and edges.
 *
 * Handles all 8 state types, creates edges for Next transitions,
 * Choice rule targets, Catch targets, and Default branches.
 */

import type { FlowNode, FlowEdge, StateType, FlowNodeData, FlowEdgeData } from '../types';

interface AstStates {
  [name: string]: Record<string, unknown>;
}

export function astToFlowElements(
  ast: Record<string, unknown>,
  existingNodes?: FlowNode[],
): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const states = (ast.States ?? ast.states ?? {}) as AstStates;
  const startAt = (ast.StartAt ?? ast.start_at ?? '') as string;

  // Build a position map from existing nodes for preservation
  const positionMap = new Map<string, { x: number; y: number }>();
  if (existingNodes) {
    for (const node of existingNodes) {
      positionMap.set(node.id, node.position);
    }
  }

  const nodes: FlowNode[] = [];
  const edges: FlowEdge[] = [];
  let yOffset = 0;

  for (const [name, stateData] of Object.entries(states)) {
    const stateType = (stateData.Type ?? stateData.type ?? 'Task') as StateType;

    const position = positionMap.get(name) ?? { x: 200, y: yOffset };
    yOffset += 120;

    const nodeData: FlowNodeData = {
      label: name,
      stateType,
      isStart: name === startAt,
      stateData,
    };

    const node: FlowNode = {
      id: name,
      type: stateType,
      position,
      data: nodeData,
    };

    nodes.push(node);

    // Create edges based on state type
    const nextState = stateData.Next as string | undefined;

    // Normal Next transition
    if (nextState) {
      edges.push(createEdge(name, nextState, 'normal'));
    }

    // Choice state: edges for each rule target and Default
    if (stateType === 'Choice') {
      const choices = (stateData.Choices ?? []) as Array<Record<string, unknown>>;
      choices.forEach((rule, idx) => {
        const ruleNext = rule.Next as string | undefined;
        if (ruleNext) {
          edges.push(
            createEdge(name, ruleNext, 'choice', `Rule ${idx + 1}`),
          );
        }
      });
      const defaultTarget = stateData.Default as string | undefined;
      if (defaultTarget) {
        edges.push(createEdge(name, defaultTarget, 'default', 'Default'));
      }
    }

    // Catch targets (Task, Parallel, Map)
    const catches = (stateData.Catch ?? []) as Array<Record<string, unknown>>;
    for (const catcher of catches) {
      const catchNext = catcher.Next as string | undefined;
      if (catchNext) {
        const errorEquals = (catcher.ErrorEquals ?? []) as string[];
        const label = errorEquals.length > 0 ? errorEquals.join(', ') : 'Catch';
        edges.push(createEdge(name, catchNext, 'catch', label));
      }
    }
  }

  return { nodes, edges };
}

function createEdge(
  source: string,
  target: string,
  edgeType: FlowEdgeData['edgeType'],
  label?: string,
): FlowEdge {
  const id = `e-${source}-${target}-${edgeType}${label ? `-${label}` : ''}`;
  return {
    id,
    source,
    target,
    type: 'transition',
    data: { edgeType, label },
  };
}
