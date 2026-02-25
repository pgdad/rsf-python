import { describe, it, expect } from 'vitest';
import { astToFlowElements } from '../sync/astToFlowElements';

describe('astToFlowElements', () => {
  it('converts a simple two-state workflow into nodes and edges', () => {
    const ast = {
      StartAt: 'Hello',
      States: {
        Hello: {
          Type: 'Task',
          Next: 'Goodbye',
        },
        Goodbye: {
          Type: 'Succeed',
        },
      },
    };

    const { nodes, edges } = astToFlowElements(ast);

    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);

    // Check node properties
    const helloNode = nodes.find((n) => n.id === 'Hello');
    expect(helloNode).toBeDefined();
    expect(helloNode!.data.label).toBe('Hello');
    expect(helloNode!.data.stateType).toBe('Task');
    expect(helloNode!.data.isStart).toBe(true);
    expect(helloNode!.type).toBe('Task');

    const goodbyeNode = nodes.find((n) => n.id === 'Goodbye');
    expect(goodbyeNode).toBeDefined();
    expect(goodbyeNode!.data.stateType).toBe('Succeed');
    expect(goodbyeNode!.data.isStart).toBe(false);

    // Check edge
    expect(edges[0].source).toBe('Hello');
    expect(edges[0].target).toBe('Goodbye');
    expect(edges[0].data?.edgeType).toBe('normal');
  });

  it('handles Choice states with rule targets and Default', () => {
    const ast = {
      StartAt: 'CheckValue',
      States: {
        CheckValue: {
          Type: 'Choice',
          Choices: [
            { Variable: '$.value', NumericEquals: 1, Next: 'ValueIsOne' },
            { Variable: '$.value', NumericEquals: 2, Next: 'ValueIsTwo' },
          ],
          Default: 'DefaultState',
        },
        ValueIsOne: { Type: 'Succeed' },
        ValueIsTwo: { Type: 'Succeed' },
        DefaultState: { Type: 'Succeed' },
      },
    };

    const { nodes, edges } = astToFlowElements(ast);

    expect(nodes).toHaveLength(4);

    // Choice edges: 2 rule edges + 1 default
    const choiceEdges = edges.filter((e) => e.source === 'CheckValue');
    expect(choiceEdges).toHaveLength(3);

    // Check rule edges
    const ruleEdges = choiceEdges.filter((e) => e.data?.edgeType === 'choice');
    expect(ruleEdges).toHaveLength(2);
    expect(ruleEdges[0].data?.label).toBe('Rule 1');
    expect(ruleEdges[1].data?.label).toBe('Rule 2');

    // Check default edge
    const defaultEdge = choiceEdges.find((e) => e.data?.edgeType === 'default');
    expect(defaultEdge).toBeDefined();
    expect(defaultEdge!.target).toBe('DefaultState');
    expect(defaultEdge!.data?.label).toBe('Default');
  });

  it('handles Catch targets on Task states', () => {
    const ast = {
      StartAt: 'DoWork',
      States: {
        DoWork: {
          Type: 'Task',
          Next: 'Done',
          Catch: [
            {
              ErrorEquals: ['States.TaskFailed'],
              Next: 'HandleError',
            },
          ],
        },
        Done: { Type: 'Succeed' },
        HandleError: { Type: 'Fail' },
      },
    };

    const { nodes, edges } = astToFlowElements(ast);

    expect(nodes).toHaveLength(3);

    // Edges: 1 normal (Next) + 1 catch
    const doWorkEdges = edges.filter((e) => e.source === 'DoWork');
    expect(doWorkEdges).toHaveLength(2);

    const normalEdge = doWorkEdges.find((e) => e.data?.edgeType === 'normal');
    expect(normalEdge).toBeDefined();
    expect(normalEdge!.target).toBe('Done');

    const catchEdge = doWorkEdges.find((e) => e.data?.edgeType === 'catch');
    expect(catchEdge).toBeDefined();
    expect(catchEdge!.target).toBe('HandleError');
    expect(catchEdge!.data?.label).toBe('States.TaskFailed');
  });

  it('handles a Pass state', () => {
    const ast = {
      StartAt: 'PassThrough',
      States: {
        PassThrough: {
          Type: 'Pass',
          Next: 'End',
        },
        End: { Type: 'Succeed' },
      },
    };

    const { nodes, edges } = astToFlowElements(ast);

    const passNode = nodes.find((n) => n.id === 'PassThrough');
    expect(passNode).toBeDefined();
    expect(passNode!.data.stateType).toBe('Pass');
    expect(passNode!.type).toBe('Pass');
    expect(edges).toHaveLength(1);
  });

  it('handles Wait, Fail, Parallel, and Map state types', () => {
    const ast = {
      StartAt: 'WaitStep',
      States: {
        WaitStep: { Type: 'Wait', Seconds: 10, Next: 'ParallelStep' },
        ParallelStep: {
          Type: 'Parallel',
          Branches: [],
          Next: 'MapStep',
        },
        MapStep: {
          Type: 'Map',
          Iterator: {},
          Next: 'FailStep',
        },
        FailStep: { Type: 'Fail', Error: 'Oops', Cause: 'Testing' },
      },
    };

    const { nodes, edges } = astToFlowElements(ast);

    expect(nodes).toHaveLength(4);
    expect(nodes.find((n) => n.data.stateType === 'Wait')).toBeDefined();
    expect(nodes.find((n) => n.data.stateType === 'Parallel')).toBeDefined();
    expect(nodes.find((n) => n.data.stateType === 'Map')).toBeDefined();
    expect(nodes.find((n) => n.data.stateType === 'Fail')).toBeDefined();

    // 3 normal transitions: Wait->Parallel, Parallel->Map, Map->Fail
    expect(edges).toHaveLength(3);
  });

  it('marks StartAt node as isStart', () => {
    const ast = {
      StartAt: 'Begin',
      States: {
        Begin: { Type: 'Task', Next: 'End' },
        End: { Type: 'Succeed' },
      },
    };

    const { nodes } = astToFlowElements(ast);
    const beginNode = nodes.find((n) => n.id === 'Begin');
    const endNode = nodes.find((n) => n.id === 'End');

    expect(beginNode!.data.isStart).toBe(true);
    expect(endNode!.data.isStart).toBe(false);
  });

  it('assigns default positions when no existing nodes are given', () => {
    const ast = {
      StartAt: 'A',
      States: {
        A: { Type: 'Task', Next: 'B' },
        B: { Type: 'Succeed' },
      },
    };

    const { nodes } = astToFlowElements(ast);

    // All nodes should have a position with x=200
    for (const node of nodes) {
      expect(node.position.x).toBe(200);
      expect(typeof node.position.y).toBe('number');
    }
  });

  it('preserves positions from existing nodes', () => {
    const ast = {
      StartAt: 'A',
      States: {
        A: { Type: 'Task', Next: 'B' },
        B: { Type: 'Succeed' },
      },
    };

    const existingNodes = [
      {
        id: 'A',
        type: 'Task',
        position: { x: 100, y: 200 },
        data: { label: 'A', stateType: 'Task' as const },
      },
    ];

    const { nodes } = astToFlowElements(ast, existingNodes);

    const nodeA = nodes.find((n) => n.id === 'A');
    expect(nodeA!.position).toEqual({ x: 100, y: 200 });

    // Node B should get default position since it wasn't in existing
    const nodeB = nodes.find((n) => n.id === 'B');
    expect(nodeB!.position.x).toBe(200);
  });

  it('handles an empty states object', () => {
    const ast = {
      StartAt: 'A',
      States: {},
    };

    const { nodes, edges } = astToFlowElements(ast);
    expect(nodes).toEqual([]);
    expect(edges).toEqual([]);
  });

  it('stores stateData on each node', () => {
    const ast = {
      StartAt: 'Greet',
      States: {
        Greet: {
          Type: 'Task',
          Resource: 'arn:aws:lambda:us-east-1:123456789:function:greet',
          Next: 'Done',
        },
        Done: { Type: 'Succeed' },
      },
    };

    const { nodes } = astToFlowElements(ast);
    const greetNode = nodes.find((n) => n.id === 'Greet');
    expect(greetNode!.data.stateData).toBeDefined();
    expect(greetNode!.data.stateData!.Resource).toBe(
      'arn:aws:lambda:us-east-1:123456789:function:greet',
    );
  });

  it('handles Catch with multiple ErrorEquals', () => {
    const ast = {
      StartAt: 'Work',
      States: {
        Work: {
          Type: 'Task',
          Next: 'Done',
          Catch: [
            {
              ErrorEquals: ['Error.A', 'Error.B'],
              Next: 'HandleMulti',
            },
          ],
        },
        Done: { Type: 'Succeed' },
        HandleMulti: { Type: 'Fail' },
      },
    };

    const { edges } = astToFlowElements(ast);
    const catchEdge = edges.find((e) => e.data?.edgeType === 'catch');
    expect(catchEdge).toBeDefined();
    expect(catchEdge!.data?.label).toBe('Error.A, Error.B');
  });
});
