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
    syncSource: null,
    needsLayout: false,
    lastAst: null,
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

function makeFlowEdge(source: string, target: string): FlowEdge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
    type: 'transition',
    data: { edgeType: 'normal' as const },
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
      useFlowStore.getState().setNodes([makeFlowNode('A')]);
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
});
