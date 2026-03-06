import { describe, it, expect, beforeEach } from 'vitest';
import { useFlowStore } from '../store/flowStore';
import type { FlowNode, FlowEdge, ValidationError } from '../types';

/**
 * Reset flow store between tests.
 */
function resetStore() {
  useFlowStore.setState({
    nodes: [],
    edges: [],
    yamlContent: '',
    validationErrors: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    expandedNodeId: null,
    toastMessage: null,
    syncSource: null,
    needsLayout: false,
    lastAst: null,
    collapseBlocked: null,
  });
}

function makeFlowNode(id: string, stateType: string = 'Task'): FlowNode {
  return {
    id,
    type: stateType,
    position: { x: 0, y: 0 },
    data: {
      label: id,
      stateType: stateType as FlowNode['data']['stateType'],
      isStart: false,
    },
  };
}

function makeFlowEdge(
  source: string,
  target: string,
  edgeType: 'normal' | 'catch' | 'default' | 'choice' = 'normal',
): FlowEdge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
    type: 'transition',
    data: { edgeType },
  };
}

describe('useFlowStore', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('initial state', () => {
    it('has correct default values', () => {
      const state = useFlowStore.getState();
      expect(state.nodes).toEqual([]);
      expect(state.edges).toEqual([]);
      expect(state.yamlContent).toBe('');
      expect(state.validationErrors).toEqual([]);
      expect(state.selectedNodeId).toBeNull();
      expect(state.selectedEdgeId).toBeNull();
      expect(state.toastMessage).toBeNull();
      expect(state.syncSource).toBeNull();
      expect(state.needsLayout).toBe(false);
      expect(state.lastAst).toBeNull();
    });
  });

  describe('setNodes', () => {
    it('replaces nodes', () => {
      const nodes = [makeFlowNode('A'), makeFlowNode('B')];
      useFlowStore.getState().setNodes(nodes);
      expect(useFlowStore.getState().nodes).toHaveLength(2);
      expect(useFlowStore.getState().nodes[0].id).toBe('A');
      expect(useFlowStore.getState().nodes[1].id).toBe('B');
    });
  });

  describe('setEdges', () => {
    it('replaces edges', () => {
      const edges = [makeFlowEdge('A', 'B')];
      useFlowStore.getState().setEdges(edges);
      expect(useFlowStore.getState().edges).toHaveLength(1);
      expect(useFlowStore.getState().edges[0].source).toBe('A');
      expect(useFlowStore.getState().edges[0].target).toBe('B');
    });
  });

  describe('setYamlContent', () => {
    it('updates the YAML content', () => {
      const yaml = 'StartAt: Hello\nStates:\n  Hello:\n    Type: Task';
      useFlowStore.getState().setYamlContent(yaml);
      expect(useFlowStore.getState().yamlContent).toBe(yaml);
    });
  });

  describe('setValidationErrors', () => {
    it('sets validation errors', () => {
      const errors: ValidationError[] = [
        { message: 'Missing Next', path: '$.States.A', severity: 'error' },
      ];
      useFlowStore.getState().setValidationErrors(errors);
      expect(useFlowStore.getState().validationErrors).toHaveLength(1);
      expect(useFlowStore.getState().validationErrors[0].message).toBe('Missing Next');
    });
  });

  describe('updateFromAst', () => {
    it('updates AST, errors, nodes, and edges together', () => {
      const ast = { StartAt: 'A', States: { A: { Type: 'Task' } } };
      const errors: ValidationError[] = [];
      const nodes = [makeFlowNode('A')];
      const edges: FlowEdge[] = [];

      useFlowStore.getState().updateFromAst(ast, errors, nodes, edges);

      const state = useFlowStore.getState();
      expect(state.lastAst).toEqual(ast);
      expect(state.validationErrors).toEqual([]);
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].id).toBe('A');
      expect(state.edges).toEqual([]);
    });
  });

  describe('addState', () => {
    it('appends a node and sets needsLayout', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      useFlowStore.getState().addState(makeFlowNode('B'));

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(2);
      expect(state.nodes[1].id).toBe('B');
      expect(state.needsLayout).toBe(true);
    });
  });

  describe('removeState', () => {
    it('removes the node and connected edges', () => {
      const nodes = [makeFlowNode('A'), makeFlowNode('B'), makeFlowNode('C')];
      const edges = [makeFlowEdge('A', 'B'), makeFlowEdge('B', 'C')];

      useFlowStore.getState().setNodes(nodes);
      useFlowStore.getState().setEdges(edges);
      useFlowStore.getState().removeState('B');

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(2);
      expect(state.nodes.map((n) => n.id)).toEqual(['A', 'C']);
      // Both edges connected to B should be removed
      expect(state.edges).toHaveLength(0);
    });

    it('clears selectedNodeId if the removed node was selected', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A'), makeFlowNode('B')]);
      useFlowStore.getState().selectNode('A');
      useFlowStore.getState().removeState('A');

      expect(useFlowStore.getState().selectedNodeId).toBeNull();
    });

    it('does not clear selectedNodeId if a different node was removed', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A'), makeFlowNode('B')]);
      useFlowStore.getState().selectNode('A');
      useFlowStore.getState().removeState('B');

      expect(useFlowStore.getState().selectedNodeId).toBe('A');
    });

    it('sets toastMessage and does NOT remove node when only 1 node exists', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      useFlowStore.getState().removeState('A');

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].id).toBe('A');
      expect(state.toastMessage).toBe('Cannot delete the only state');
    });

    it('reassigns isStart to alphabetically first remaining node when start node is deleted (A, B, C: delete A)', () => {
      const nodeA = { ...makeFlowNode('A'), data: { ...makeFlowNode('A').data, isStart: true } };
      const nodeB = makeFlowNode('B');
      const nodeC = makeFlowNode('C');
      useFlowStore.getState().setNodes([nodeA, nodeB, nodeC]);
      useFlowStore.getState().removeState('A');

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(2);
      const startNodes = state.nodes.filter((n) => n.data.isStart);
      expect(startNodes).toHaveLength(1);
      expect(startNodes[0].id).toBe('B');
    });

    it('reassigns isStart to alphabetically first remaining node (C, A, B: delete C)', () => {
      const nodeC = { ...makeFlowNode('C'), data: { ...makeFlowNode('C').data, isStart: true } };
      const nodeA = makeFlowNode('A');
      const nodeB = makeFlowNode('B');
      useFlowStore.getState().setNodes([nodeC, nodeA, nodeB]);
      useFlowStore.getState().removeState('C');

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(2);
      const startNodes = state.nodes.filter((n) => n.data.isStart);
      expect(startNodes).toHaveLength(1);
      expect(startNodes[0].id).toBe('A');
    });

    it('does not change isStart flags when a non-start node is removed', () => {
      const nodeA = { ...makeFlowNode('A'), data: { ...makeFlowNode('A').data, isStart: true } };
      const nodeB = makeFlowNode('B');
      const nodeC = makeFlowNode('C');
      useFlowStore.getState().setNodes([nodeA, nodeB, nodeC]);
      useFlowStore.getState().removeState('C');

      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(2);
      const startNodes = state.nodes.filter((n) => n.data.isStart);
      expect(startNodes).toHaveLength(1);
      expect(startNodes[0].id).toBe('A');
    });

    it('clears selectedEdgeId when a node is removed', () => {
      const nodeA = makeFlowNode('A');
      const nodeB = makeFlowNode('B');
      useFlowStore.getState().setNodes([nodeA, nodeB]);
      useFlowStore.setState({ selectedEdgeId: 'e-A-B' });
      useFlowStore.getState().removeState('B');

      expect(useFlowStore.getState().selectedEdgeId).toBeNull();
    });
  });

  describe('selectNode', () => {
    it('sets the selected node', () => {
      useFlowStore.getState().selectNode('node-1');
      expect(useFlowStore.getState().selectedNodeId).toBe('node-1');
    });

    it('clears selection with null', () => {
      useFlowStore.getState().selectNode('node-1');
      useFlowStore.getState().selectNode(null);
      expect(useFlowStore.getState().selectedNodeId).toBeNull();
    });

    it('clears selectedEdgeId when a node is selected (mutual exclusion)', () => {
      useFlowStore.getState().selectEdge('edge-1');
      expect(useFlowStore.getState().selectedEdgeId).toBe('edge-1');

      useFlowStore.getState().selectNode('node-1');
      expect(useFlowStore.getState().selectedNodeId).toBe('node-1');
      expect(useFlowStore.getState().selectedEdgeId).toBeNull();
    });
  });

  describe('selectEdge', () => {
    it('sets selectedEdgeId', () => {
      useFlowStore.getState().selectEdge('edge-1');
      expect(useFlowStore.getState().selectedEdgeId).toBe('edge-1');
    });

    it('clears selectedEdgeId with null', () => {
      useFlowStore.getState().selectEdge('edge-1');
      useFlowStore.getState().selectEdge(null);
      expect(useFlowStore.getState().selectedEdgeId).toBeNull();
    });

    it('clears selectedNodeId when an edge is selected (mutual exclusion)', () => {
      useFlowStore.getState().selectNode('node-1');
      expect(useFlowStore.getState().selectedNodeId).toBe('node-1');

      useFlowStore.getState().selectEdge('edge-1');
      expect(useFlowStore.getState().selectedEdgeId).toBe('edge-1');
      expect(useFlowStore.getState().selectedNodeId).toBeNull();
    });
  });

  describe('removeEdge', () => {
    it('removes a normal edge and clears selectedEdgeId', () => {
      const edge = makeFlowEdge('A', 'B', 'normal');
      useFlowStore.getState().setEdges([edge]);
      useFlowStore.getState().selectEdge(edge.id);
      useFlowStore.getState().removeEdge(edge.id);

      const state = useFlowStore.getState();
      expect(state.edges).toHaveLength(0);
      expect(state.selectedEdgeId).toBeNull();
    });

    it('removes a default edge', () => {
      const edge = makeFlowEdge('A', 'B', 'default');
      useFlowStore.getState().setEdges([edge]);
      useFlowStore.getState().removeEdge(edge.id);

      expect(useFlowStore.getState().edges).toHaveLength(0);
    });

    it('does NOT remove a catch edge and sets toastMessage', () => {
      const edge = makeFlowEdge('A', 'B', 'catch');
      useFlowStore.getState().setEdges([edge]);
      useFlowStore.getState().removeEdge(edge.id);

      const state = useFlowStore.getState();
      expect(state.edges).toHaveLength(1);
      expect(state.toastMessage).toBe('Catch edges must be edited in YAML');
    });

    it('does NOT remove a choice edge and sets toastMessage', () => {
      const edge = makeFlowEdge('A', 'B', 'choice');
      useFlowStore.getState().setEdges([edge]);
      useFlowStore.getState().removeEdge(edge.id);

      const state = useFlowStore.getState();
      expect(state.edges).toHaveLength(1);
      expect(state.toastMessage).toBe('Choice rule edges must be edited in YAML');
    });
  });

  describe('clearSelection', () => {
    it('clears both selectedNodeId and selectedEdgeId', () => {
      useFlowStore.getState().selectNode('node-1');
      // Manually set selectedEdgeId without going through selectEdge
      // (since selectEdge clears selectedNodeId)
      useFlowStore.setState({ selectedEdgeId: 'edge-1', selectedNodeId: 'node-1' });

      useFlowStore.getState().clearSelection();

      const state = useFlowStore.getState();
      expect(state.selectedNodeId).toBeNull();
      expect(state.selectedEdgeId).toBeNull();
    });
  });

  describe('setSyncSource', () => {
    it('updates the sync source', () => {
      useFlowStore.getState().setSyncSource('editor');
      expect(useFlowStore.getState().syncSource).toBe('editor');
      useFlowStore.getState().setSyncSource('graph');
      expect(useFlowStore.getState().syncSource).toBe('graph');
      useFlowStore.getState().setSyncSource(null);
      expect(useFlowStore.getState().syncSource).toBeNull();
    });
  });

  describe('setNeedsLayout', () => {
    it('sets needsLayout flag', () => {
      useFlowStore.getState().setNeedsLayout(true);
      expect(useFlowStore.getState().needsLayout).toBe(true);
      useFlowStore.getState().setNeedsLayout(false);
      expect(useFlowStore.getState().needsLayout).toBe(false);
    });
  });

  describe('onConnect', () => {
    it('adds a new edge from a connection', () => {
      useFlowStore.getState().onConnect({
        source: 'A',
        target: 'B',
        sourceHandle: null,
        targetHandle: null,
      });

      const state = useFlowStore.getState();
      expect(state.edges).toHaveLength(1);
      expect(state.edges[0].id).toBe('e-A-B');
      expect(state.edges[0].source).toBe('A');
      expect(state.edges[0].target).toBe('B');
      expect(state.edges[0].data?.edgeType).toBe('normal');
    });
  });

  describe('expandedNodeId initial state', () => {
    it('is null by default', () => {
      const state = useFlowStore.getState();
      expect(state.expandedNodeId).toBeNull();
    });
  });

  describe('toggleExpand', () => {
    it('sets expandedNodeId to the given node when no node is expanded', () => {
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBe('A');
    });

    it('collapses (sets to null) when toggling the already-expanded node', () => {
      useFlowStore.getState().toggleExpand('A');
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('switches to new node (accordion) when a different node is already expanded', () => {
      useFlowStore.getState().toggleExpand('A');
      useFlowStore.getState().toggleExpand('B');
      expect(useFlowStore.getState().expandedNodeId).toBe('B');
    });
  });

  describe('toggleExpand — validation guard', () => {
    it('expanding always works regardless of stateData content', () => {
      // Task node with no stateData — expand should always succeed
      const taskNode = makeFlowNode('A', 'Task');
      useFlowStore.getState().setNodes([taskNode]);
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBe('A');
    });

    it('Task node with stateData.Resource empty: collapse is NOT blocked (Task has no Pydantic-required fields)', () => {
      const taskNode: FlowNode = {
        ...makeFlowNode('A', 'Task'),
        data: { ...makeFlowNode('A', 'Task').data, stateData: { Resource: '' } },
      };
      useFlowStore.getState().setNodes([taskNode]);
      useFlowStore.getState().toggleExpand('A'); // expand
      useFlowStore.getState().toggleExpand('A'); // collapse — should succeed
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('Task node with stateData.Resource set: collapse allowed', () => {
      const taskNode: FlowNode = {
        ...makeFlowNode('A', 'Task'),
        data: {
          ...makeFlowNode('A', 'Task').data,
          stateData: { Resource: 'arn:aws:lambda:us-east-1:123456789:function:myFn' },
        },
      };
      useFlowStore.getState().setNodes([taskNode]);
      useFlowStore.getState().toggleExpand('A');
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('Succeed node (no required fields): collapse always allowed', () => {
      const succeedNode = makeFlowNode('A', 'Succeed');
      useFlowStore.getState().setNodes([succeedNode]);
      useFlowStore.getState().toggleExpand('A');
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('Wait node with none of Seconds/Timestamp/SecondsPath/TimestampPath set: blocks collapse', () => {
      const waitNode: FlowNode = {
        ...makeFlowNode('W', 'Wait'),
        data: { ...makeFlowNode('W', 'Wait').data, stateData: {} },
      };
      useFlowStore.getState().setNodes([waitNode]);
      useFlowStore.getState().toggleExpand('W'); // expand
      useFlowStore.getState().toggleExpand('W'); // collapse — should be blocked
      expect(useFlowStore.getState().expandedNodeId).toBe('W');
      expect(useFlowStore.getState().toastMessage).toBeTruthy();
      expect(useFlowStore.getState().collapseBlocked).toBe('W');
    });

    it('Wait node with Seconds set: collapse allowed', () => {
      const waitNode: FlowNode = {
        ...makeFlowNode('W', 'Wait'),
        data: { ...makeFlowNode('W', 'Wait').data, stateData: { Seconds: 30 } },
      };
      useFlowStore.getState().setNodes([waitNode]);
      useFlowStore.getState().toggleExpand('W');
      useFlowStore.getState().toggleExpand('W');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('Wait node with Timestamp set: collapse allowed', () => {
      const waitNode: FlowNode = {
        ...makeFlowNode('W', 'Wait'),
        data: {
          ...makeFlowNode('W', 'Wait').data,
          stateData: { Timestamp: '2024-01-01T00:00:00Z' },
        },
      };
      useFlowStore.getState().setNodes([waitNode]);
      useFlowStore.getState().toggleExpand('W');
      useFlowStore.getState().toggleExpand('W');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('collapseBlocked is cleared on the next toggleExpand call (expand)', () => {
      const waitNode: FlowNode = {
        ...makeFlowNode('W', 'Wait'),
        data: { ...makeFlowNode('W', 'Wait').data, stateData: {} },
      };
      useFlowStore.getState().setNodes([waitNode]);
      useFlowStore.getState().toggleExpand('W'); // expand
      useFlowStore.getState().toggleExpand('W'); // blocked collapse
      expect(useFlowStore.getState().collapseBlocked).toBe('W');

      // Add Seconds so next collapse will work; re-expand another node clears blocked
      const waitNode2 = makeFlowNode('X', 'Succeed');
      useFlowStore.getState().setNodes([...useFlowStore.getState().nodes, waitNode2]);
      useFlowStore.getState().toggleExpand('X'); // switch to X — clears collapseBlocked
      expect(useFlowStore.getState().collapseBlocked).toBeNull();
    });
  });

  describe('updateStateProperty', () => {
    it('sets a string property on a node stateData', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      useFlowStore.getState().updateStateProperty('A', 'Comment', 'hello');
      const node = useFlowStore.getState().nodes.find((n) => n.id === 'A');
      expect(node?.data.stateData?.Comment).toBe('hello');
    });

    it('sets a numeric property on a node stateData', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      useFlowStore.getState().updateStateProperty('A', 'TimeoutSeconds', 30);
      const node = useFlowStore.getState().nodes.find((n) => n.id === 'A');
      expect(node?.data.stateData?.TimeoutSeconds).toBe(30);
    });

    it('sets a boolean property on a node stateData', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      useFlowStore.getState().updateStateProperty('A', 'End', true);
      const node = useFlowStore.getState().nodes.find((n) => n.id === 'A');
      expect(node?.data.stateData?.End).toBe(true);
    });

    it('is a no-op when node does not exist', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
      // Should not throw
      useFlowStore.getState().updateStateProperty('NonExistent', 'Comment', 'hello');
      const state = useFlowStore.getState();
      expect(state.nodes).toHaveLength(1);
    });

    it('initializes stateData as {} if undefined before setting property', () => {
      const node = makeFlowNode('A');
      // makeFlowNode does not set stateData, so it is undefined
      useFlowStore.getState().setNodes([node]);
      expect(useFlowStore.getState().nodes[0].data.stateData).toBeUndefined();
      useFlowStore.getState().updateStateProperty('A', 'Comment', 'init-test');
      const updated = useFlowStore.getState().nodes.find((n) => n.id === 'A');
      expect(updated?.data.stateData).toBeDefined();
      expect(updated?.data.stateData?.Comment).toBe('init-test');
    });
  });

  describe('removeState clears expandedNodeId', () => {
    it('clears expandedNodeId when the expanded node is deleted', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A'), makeFlowNode('B')]);
      useFlowStore.getState().toggleExpand('A');
      expect(useFlowStore.getState().expandedNodeId).toBe('A');

      useFlowStore.getState().removeState('A');
      expect(useFlowStore.getState().expandedNodeId).toBeNull();
    });

    it('does not clear expandedNodeId when a different node is deleted', () => {
      useFlowStore.getState().setNodes([makeFlowNode('A'), makeFlowNode('B')]);
      useFlowStore.getState().toggleExpand('A');
      useFlowStore.getState().removeState('B');

      expect(useFlowStore.getState().expandedNodeId).toBe('A');
    });
  });
});
