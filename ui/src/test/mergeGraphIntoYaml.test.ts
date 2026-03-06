import { describe, it, expect } from 'vitest';
import { mergeGraphIntoYaml } from '../sync/mergeGraphIntoYaml';
import * as yaml from 'js-yaml';
import type { FlowNode, FlowEdge } from '../types';

function makeNode(id: string, stateType: 'Task' | 'Choice' | 'Pass' = 'Task', isStart = false): FlowNode {
  return {
    id,
    type: stateType,
    position: { x: 0, y: 0 },
    data: {
      label: id,
      stateType,
      isStart,
    },
  };
}

function makeEdge(
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

describe('mergeGraphIntoYaml', () => {
  describe('removing a normal edge from a Task state', () => {
    it('results in End:true and no Next key for that state', () => {
      // Initial AST: A -> B (Task state with Next: B)
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: { Type: 'Task', Next: 'B' },
          B: { Type: 'Task', End: true },
        },
      };

      // After removing edge A->B, A has no outgoing normal edges
      const nodes = [makeNode('A', 'Task', true), makeNode('B')];
      const edges: FlowEdge[] = []; // Edge removed

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['A']).not.toHaveProperty('Next');
      expect(states['A']['End']).toBe(true);
    });

    it('keeps the edge in AST if the normal edge still exists', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: { Type: 'Task', Next: 'B' },
          B: { Type: 'Task', End: true },
        },
      };

      const nodes = [makeNode('A', 'Task', true), makeNode('B')];
      const edges = [makeEdge('A', 'B', 'normal')];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['A']['Next']).toBe('B');
      expect(states['A']).not.toHaveProperty('End');
    });
  });

  describe('removing the Default edge from a Choice state', () => {
    it('results in no Default key in that state', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'Router',
        States: {
          Router: {
            Type: 'Choice',
            Choices: [{ Variable: '$.x', NumericEquals: 1, Next: 'B' }],
            Default: 'C',
          },
          B: { Type: 'Task', End: true },
          C: { Type: 'Task', End: true },
        },
      };

      // After removing the default edge from Router
      const nodes = [makeNode('Router', 'Choice', true), makeNode('B'), makeNode('C')];
      const edges: FlowEdge[] = [
        // Only choice rule edge remains, no default edge
        makeEdge('Router', 'B', 'choice'),
      ];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['Router']).not.toHaveProperty('Default');
    });

    it('preserves Default key when default edge still exists', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'Router',
        States: {
          Router: {
            Type: 'Choice',
            Choices: [{ Variable: '$.x', NumericEquals: 1, Next: 'B' }],
            Default: 'C',
          },
          B: { Type: 'Task', End: true },
          C: { Type: 'Task', End: true },
        },
      };

      const nodes = [makeNode('Router', 'Choice', true), makeNode('B'), makeNode('C')];
      const edges: FlowEdge[] = [
        makeEdge('Router', 'B', 'choice'),
        makeEdge('Router', 'C', 'default'),
      ];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['Router']['Default']).toBe('C');
    });
  });

  describe('reference cleanup when a node is deleted', () => {
    it("sets End:true on a state whose Next points to a node that no longer exists", () => {
      // A -> B, now B is deleted from nodes. A's Next still points to B in AST but B is gone.
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: { Type: 'Task', Next: 'B' },
          B: { Type: 'Task', End: true },
        },
      };

      // B has been removed from nodes, edge also removed
      const nodes = [makeNode('A', 'Task', true)];
      const edges: FlowEdge[] = [];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['A']).not.toHaveProperty('Next');
      expect(states['A']['End']).toBe(true);
      expect(states).not.toHaveProperty('B');
    });

    it('updates StartAt to the node with isStart=true when start node changes', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: { Type: 'Task', Next: 'B' },
          B: { Type: 'Task', End: true },
        },
      };

      // A was deleted, B is now start
      const nodes = [makeNode('B', 'Task', true)];
      const edges: FlowEdge[] = [];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;

      expect(parsed['StartAt']).toBe('B');
      const states = parsed.States as Record<string, Record<string, unknown>>;
      expect(states).not.toHaveProperty('A');
      expect(states['B']['End']).toBe(true);
    });

    it("removes Default from Choice state whose Default target no longer exists", () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'Router',
        States: {
          Router: {
            Type: 'Choice',
            Choices: [{ Variable: '$.x', NumericEquals: 1, Next: 'B' }],
            Default: 'C',
          },
          B: { Type: 'Task', End: true },
          C: { Type: 'Task', End: true },
        },
      };

      // C is deleted from nodes, C's default edge also removed
      const nodes = [makeNode('Router', 'Choice', true), makeNode('B')];
      const edges: FlowEdge[] = [makeEdge('Router', 'B', 'choice')];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['Router']).not.toHaveProperty('Default');
      expect(states).not.toHaveProperty('C');
    });

    it('3-state chain A->B->C: removing B produces A with End:true and C with End:true', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: { Type: 'Task', Next: 'B' },
          B: { Type: 'Task', Next: 'C' },
          C: { Type: 'Task', End: true },
        },
      };

      // B is removed; edges A->B and B->C are also removed
      const nodes = [makeNode('A', 'Task', true), makeNode('C')];
      const edges: FlowEdge[] = [];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states).not.toHaveProperty('B');
      expect(states['A']).not.toHaveProperty('Next');
      expect(states['A']['End']).toBe(true);
      expect(states['C']['End']).toBe(true);
    });
  });

  describe('catch edges and choice rule edges', () => {
    it('preserves Catch arrays in AST even when no catch edges are in graph', () => {
      // Catch edges are complex data — removing them from graph should not change Catch array
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'A',
        States: {
          A: {
            Type: 'Task',
            Next: 'B',
            Catch: [{ ErrorEquals: ['States.ALL'], Next: 'ErrorHandler' }],
          },
          B: { Type: 'Task', End: true },
          ErrorHandler: { Type: 'Task', End: true },
        },
      };

      // No catch edges in graph (they're not shown as removable)
      const nodes = [makeNode('A', 'Task', true), makeNode('B'), makeNode('ErrorHandler')];
      const edges = [makeEdge('A', 'B', 'normal')];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      // Catch array should remain intact
      expect(states['A']['Catch']).toBeDefined();
      expect((states['A']['Catch'] as unknown[]).length).toBe(1);
    });

    it('preserves Choice rules (Choices array) even when choice edges are removed from graph', () => {
      const lastAst = {
        rsf_version: '1.0',
        StartAt: 'Router',
        States: {
          Router: {
            Type: 'Choice',
            Choices: [
              { Variable: '$.x', NumericEquals: 1, Next: 'B' },
              { Variable: '$.x', NumericEquals: 2, Next: 'C' },
            ],
          },
          B: { Type: 'Task', End: true },
          C: { Type: 'Task', End: true },
        },
      };

      const nodes = [makeNode('Router', 'Choice', true), makeNode('B'), makeNode('C')];
      // No choice edges in graph (removed), but AST should preserve Choices
      const edges: FlowEdge[] = [];

      const result = mergeGraphIntoYaml(lastAst, nodes, edges);
      const parsed = yaml.load(result) as Record<string, unknown>;
      const states = parsed.States as Record<string, Record<string, unknown>>;

      expect(states['Router']['Choices']).toBeDefined();
      expect((states['Router']['Choices'] as unknown[]).length).toBe(2);
    });
  });
});
