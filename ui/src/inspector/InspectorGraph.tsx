/**
 * InspectorGraph - Center panel showing the workflow graph with overlays.
 *
 * Renders the workflow graph from the execution's state machine definition
 * with node overlays (status, timing, I/O, retry) and edge overlays
 * (traversed flag, timestamp).
 */

import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  type NodeTypes,
  type EdgeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useInspectStore, type InspectNode } from '../store/inspectStore';
import { InspectorNode } from './InspectorNode';
import { InspectorEdge } from './InspectorEdge';

const nodeTypes: NodeTypes = {
  Task: InspectorNode,
  Pass: InspectorNode,
  Choice: InspectorNode,
  Wait: InspectorNode,
  Succeed: InspectorNode,
  Fail: InspectorNode,
  Parallel: InspectorNode,
  Map: InspectorNode,
} as NodeTypes;

const edgeTypes: EdgeTypes = {
  transition: InspectorEdge,
} as EdgeTypes;

export function InspectorGraph() {
  const nodes = useInspectStore((s) => s.nodes);
  const edges = useInspectStore((s) => s.edges);
  const snapshots = useInspectStore((s) => s.snapshots);
  const playbackIndex = useInspectStore((s) => s.playbackIndex);
  const selectNode = useInspectStore((s) => s.selectNode);

  // Apply overlay data from current snapshot to nodes
  const overlaidNodes = useMemo(() => {
    if (playbackIndex < 0 || playbackIndex >= snapshots.length) return nodes;
    const snap = snapshots[playbackIndex];
    return nodes.map((node) => {
      const overlay = snap.nodeOverlays[node.id];
      if (overlay) {
        return {
          ...node,
          data: { ...node.data, overlay },
        } as InspectNode;
      }
      return node;
    });
  }, [nodes, snapshots, playbackIndex]);

  // Apply overlay data from current snapshot to edges
  const overlaidEdges = useMemo(() => {
    if (playbackIndex < 0 || playbackIndex >= snapshots.length) return edges;
    const snap = snapshots[playbackIndex];
    return edges.map((edge) => {
      const overlay = snap.edgeOverlays[edge.id];
      if (overlay) {
        return {
          ...edge,
          data: { ...edge.data, overlay },
        };
      }
      return edge;
    });
  }, [edges, snapshots, playbackIndex]);

  const handlePaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const executionDetail = useInspectStore((s) => s.executionDetail);

  if (!executionDetail) {
    return (
      <div className="inspector-graph-empty">
        <div className="inspector-graph-placeholder">
          Select an execution to inspect
        </div>
      </div>
    );
  }

  return (
    <div className="inspector-graph">
      <ReactFlow
        nodes={overlaidNodes}
        edges={overlaidEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onPaneClick={handlePaneClick}
        onNodeClick={(_e, node) => selectNode(node.id)}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        defaultEdgeOptions={{
          type: 'transition',
          animated: false,
        }}
      >
        <Controls />
        <MiniMap />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
      </ReactFlow>
    </div>
  );
}
