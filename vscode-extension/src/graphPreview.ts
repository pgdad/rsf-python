/**
 * Graph conversion utilities — parse workflow YAML into nodes/edges
 * and apply layout using dagre for clean directed-graph rendering.
 */

import dagre from "dagre";

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  hasError: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/**
 * Convert parsed workflow YAML data into a graph structure.
 */
export function yamlToGraph(data: any): GraphData {
  if (!data || !data.States || typeof data.States !== "object") {
    return { nodes: [], edges: [] };
  }

  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const states = data.States;

  // Create nodes for each state
  for (const [name, state] of Object.entries<any>(states)) {
    const stateType = state?.Type || "Unknown";
    nodes.push({
      id: name,
      label: name,
      type: stateType,
      x: 0,
      y: 0,
      width: stateType === "Choice" ? 160 : 140,
      height: stateType === "Choice" ? 70 : 50,
      hasError: false,
    });

    // Collect edges
    if (state.Next) {
      edges.push({ source: name, target: state.Next });
    }

    if (state.Type === "Choice") {
      if (state.Default) {
        edges.push({ source: name, target: state.Default, label: "Default" });
      }
      if (state.Choices) {
        for (let i = 0; i < state.Choices.length; i++) {
          const choice = state.Choices[i];
          if (choice.Next) {
            const condLabel = extractChoiceLabel(choice, i);
            edges.push({ source: name, target: choice.Next, label: condLabel });
          }
          // Handle boolean combinators
          collectChoiceEdges(choice, name, edges, i);
        }
      }
    }

    if (state.Catch) {
      for (const catcher of state.Catch) {
        if (catcher.Next) {
          edges.push({
            source: name,
            target: catcher.Next,
            label: "Catch",
          });
        }
      }
    }
  }

  return { nodes, edges };
}

function extractChoiceLabel(choice: any, index: number): string {
  if (choice.Variable && choice.StringEquals) {
    return `${choice.Variable} == "${choice.StringEquals}"`;
  }
  if (choice.Variable && choice.NumericEquals !== undefined) {
    return `${choice.Variable} == ${choice.NumericEquals}`;
  }
  if (choice.Variable && choice.BooleanEquals !== undefined) {
    return `${choice.Variable} == ${choice.BooleanEquals}`;
  }
  return `Rule ${index + 1}`;
}

function collectChoiceEdges(
  rule: any,
  sourceName: string,
  edges: GraphEdge[],
  index: number
): void {
  const subRules = rule.And || rule.Or || [];
  for (const sub of subRules) {
    if (sub.Next && sub.Next !== rule.Next) {
      edges.push({
        source: sourceName,
        target: sub.Next,
        label: `Rule ${index + 1}`,
      });
    }
    collectChoiceEdges(sub, sourceName, edges, index);
  }
  if (rule.Not?.Next) {
    edges.push({
      source: sourceName,
      target: rule.Not.Next,
      label: `Not Rule ${index + 1}`,
    });
  }
}

/**
 * Apply dagre layout algorithm for clean top-to-bottom directed graph.
 */
export function layoutGraph(graphData: GraphData): GraphData {
  if (graphData.nodes.length === 0) return graphData;

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "TB",
    nodesep: 50,
    ranksep: 80,
    marginx: 20,
    marginy: 20,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of graphData.nodes) {
    g.setNode(node.id, { width: node.width, height: node.height });
  }

  for (const edge of graphData.edges) {
    // Only add edges between existing nodes
    if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
      g.setEdge(edge.source, edge.target);
    }
  }

  dagre.layout(g);

  const layoutNodes = graphData.nodes.map((node) => {
    const layoutNode = g.node(node.id);
    return {
      ...node,
      x: layoutNode?.x ?? 0,
      y: layoutNode?.y ?? 0,
    };
  });

  return { nodes: layoutNodes, edges: graphData.edges };
}

/**
 * Mark nodes that have validation errors with red border highlight.
 */
export function applyErrorHighlights(
  graphData: GraphData,
  errorStateNames: string[]
): GraphData {
  const errorSet = new Set(errorStateNames);
  const nodes = graphData.nodes.map((node) => ({
    ...node,
    hasError: errorSet.has(node.id),
  }));
  return { nodes, edges: graphData.edges };
}

/**
 * Extract state names that have errors from diagnostic messages.
 */
export function extractErrorStateNames(errors: any[]): string[] {
  const stateNames = new Set<string>();

  for (const err of errors) {
    const message = err.message || "";
    // Match patterns like "State 'ProcessOrder' is not reachable"
    const stateMatch = message.match(/State '(\w+)'/);
    if (stateMatch) stateNames.add(stateMatch[1]);

    // Match patterns like "Next 'ProcessOrder' does not reference"
    const nextMatch = message.match(/(?:Next|Default) '(\w+)'/);
    if (nextMatch) stateNames.add(nextMatch[1]);

    // From source path like "States.ProcessOrder.Next"
    const source = err.source || "";
    const pathMatch =
      source.match?.(/States\.(\w+)/) ||
      message.match(/States\.(\w+)/);
    if (pathMatch) stateNames.add(pathMatch[1]);
  }

  return [...stateNames];
}
