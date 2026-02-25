/**
 * Graph → YAML sync: AST-merge strategy.
 *
 * Clones the last parsed AST, updates only transitions (Next/Default/End),
 * preserves complex data (Choice rules, Catch arrays, Parallel branches).
 * Falls back to buildYamlFromNodes if no prior AST exists.
 */

import * as yaml from 'js-yaml';
import type { FlowNode, FlowEdge } from '../types';

/**
 * Merge graph changes into YAML using AST-merge strategy.
 * This preserves all complex state data that the graph can't represent.
 */
export function mergeGraphIntoYaml(
  lastAst: Record<string, unknown> | null,
  nodes: FlowNode[],
  edges: FlowEdge[],
): string {
  if (!lastAst) {
    return buildYamlFromNodes(nodes, edges);
  }

  // Deep clone the AST to avoid mutation
  const ast = JSON.parse(JSON.stringify(lastAst)) as Record<string, unknown>;
  const states = (ast.States ?? {}) as Record<string, Record<string, unknown>>;

  // Build edge lookup: source → targets with edge type
  const edgesBySource = new Map<
    string,
    Array<{ target: string; edgeType: string; label?: string }>
  >();
  for (const edge of edges) {
    const list = edgesBySource.get(edge.source) ?? [];
    list.push({
      target: edge.target,
      edgeType: edge.data?.edgeType ?? 'normal',
      label: edge.data?.label,
    });
    edgesBySource.set(edge.source, list);
  }

  // Track which nodes still exist
  const existingNodeIds = new Set(nodes.map((n) => n.id));

  // Remove states that no longer have nodes
  for (const stateName of Object.keys(states)) {
    if (!existingNodeIds.has(stateName)) {
      delete states[stateName];
    }
  }

  // Add new nodes that don't exist in the AST yet
  for (const node of nodes) {
    if (!states[node.id]) {
      states[node.id] = {
        Type: node.data.stateType,
        End: true,
      };
    }
  }

  // Update transitions for each state
  for (const node of nodes) {
    const state = states[node.id];
    if (!state) continue;

    const stateType = (state.Type ?? 'Task') as string;
    const outEdges = edgesBySource.get(node.id) ?? [];

    if (stateType === 'Choice') {
      // Choice states: update Default, leave Choices rules alone
      const defaultEdge = outEdges.find((e) => e.edgeType === 'default');
      if (defaultEdge) {
        state.Default = defaultEdge.target;
      } else {
        delete state.Default;
      }
      // Don't modify Choice rules — they contain complex data we can't rebuild
    } else if (stateType !== 'Succeed' && stateType !== 'Fail') {
      // Normal transitioning states: update Next/End
      const normalEdge = outEdges.find(
        (e) => e.edgeType === 'normal' || e.edgeType === undefined,
      );
      if (normalEdge) {
        state.Next = normalEdge.target;
        delete state.End;
      } else {
        delete state.Next;
        state.End = true;
      }
    }
    // Catch edges: don't modify — Catch arrays contain complex data
  }

  // Update StartAt based on isStart flag
  const startNode = nodes.find((n) => n.data.isStart);
  if (startNode) {
    ast.StartAt = startNode.id;
  }

  ast.States = states;
  return yaml.dump(ast, { lineWidth: -1, noRefs: true, sortKeys: false });
}

/**
 * Fallback: build YAML from scratch based on nodes and edges.
 * Used when no prior AST exists.
 */
export function buildYamlFromNodes(
  nodes: FlowNode[],
  edges: FlowEdge[],
): string {
  if (nodes.length === 0) return '';

  const edgesBySource = new Map<string, string>();
  for (const edge of edges) {
    if (edge.data?.edgeType === 'normal' || !edge.data?.edgeType) {
      edgesBySource.set(edge.source, edge.target);
    }
  }

  const startNode = nodes.find((n) => n.data.isStart) ?? nodes[0];

  const states: Record<string, Record<string, unknown>> = {};
  for (const node of nodes) {
    const state: Record<string, unknown> = {
      Type: node.data.stateType,
    };

    const target = edgesBySource.get(node.id);
    if (target) {
      state.Next = target;
    } else if (node.data.stateType !== 'Choice') {
      state.End = true;
    }

    states[node.id] = state;
  }

  const ast = {
    rsf_version: '1.0',
    StartAt: startNode.id,
    States: states,
  };

  return yaml.dump(ast, { lineWidth: -1, noRefs: true, sortKeys: false });
}
