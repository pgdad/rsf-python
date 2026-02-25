/**
 * ELK.js auto-layout using the Sugiyama layered algorithm.
 *
 * Triggered on first load, node add/remove, and explicit layout requests.
 */

import ELK, { type ElkNode, type ElkExtendedEdge } from 'elkjs/lib/elk.bundled.js';
import type { FlowNode, FlowEdge } from '../types';

const elk = new ELK();

const DEFAULT_NODE_WIDTH = 180;
const DEFAULT_NODE_HEIGHT = 80;

export async function getLayoutedElements(
  nodes: FlowNode[],
  edges: FlowEdge[],
): Promise<{ nodes: FlowNode[]; edges: FlowEdge[] }> {
  if (nodes.length === 0) return { nodes, edges };

  const elkNodes: ElkNode[] = nodes.map((node) => ({
    id: node.id,
    width: DEFAULT_NODE_WIDTH,
    height: DEFAULT_NODE_HEIGHT,
  }));

  const elkEdges: ElkExtendedEdge[] = edges.map((edge) => ({
    id: edge.id,
    sources: [edge.source],
    targets: [edge.target],
  }));

  const graph: ElkNode = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80',
      'elk.spacing.nodeNode': '40',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    },
    children: elkNodes,
    edges: elkEdges,
  };

  const layoutedGraph = await elk.layout(graph);

  const layoutedNodes = nodes.map((node) => {
    const elkNode = layoutedGraph.children?.find((n) => n.id === node.id);
    if (elkNode) {
      return {
        ...node,
        position: {
          x: elkNode.x ?? 0,
          y: elkNode.y ?? 0,
        },
      };
    }
    return node;
  });

  return { nodes: layoutedNodes, edges };
}
