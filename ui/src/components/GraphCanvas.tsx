/**
 * Graph canvas component using @xyflow/react.
 * Renders the workflow graph with minimap, controls, and background grid.
 * Supports drag-drop from palette, edge selection/deletion, and keyboard shortcuts.
 */

import { useCallback, useEffect, useRef, type DragEvent } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useFlowStore } from '../store/flowStore';
import { nodeTypes } from '../nodes';
import { edgeTypes } from '../edges';
import type { FlowNode, StateType, FlowNodeData } from '../types';

interface GraphCanvasProps {
  onGraphChange?: () => void;
}

export function GraphCanvas({ onGraphChange }: GraphCanvasProps) {
  const nodes = useFlowStore((s) => s.nodes);
  const edges = useFlowStore((s) => s.edges);
  const onNodesChange = useFlowStore((s) => s.onNodesChange);
  const onEdgesChange = useFlowStore((s) => s.onEdgesChange);
  const onConnect = useFlowStore((s) => s.onConnect);
  const addState = useFlowStore((s) => s.addState);
  const selectNode = useFlowStore((s) => s.selectNode);
  const selectEdge = useFlowStore((s) => s.selectEdge);
  const removeEdge = useFlowStore((s) => s.removeEdge);
  const clearSelection = useFlowStore((s) => s.clearSelection);
  const selectedEdgeId = useFlowStore((s) => s.selectedEdgeId);
  const toastMessage = useFlowStore((s) => s.toastMessage);
  const setToastMessage = useFlowStore((s) => s.setToastMessage);

  const containerRef = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // Auto-dismiss toast after 2500ms
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => {
      setToastMessage(null);
    }, 2500);
    return () => clearTimeout(timer);
  }, [toastMessage, setToastMessage]);

  // Keyboard listener on the graph container div (not document — avoids Monaco conflicts)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Delete' || event.key === 'Backspace') {
        const currentSelectedEdgeId = useFlowStore.getState().selectedEdgeId;
        if (currentSelectedEdgeId) {
          event.preventDefault();
          removeEdge(currentSelectedEdgeId);
          onGraphChange?.();
        }
      } else if (event.key === 'Escape') {
        clearSelection();
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [removeEdge, clearSelection, onGraphChange]);

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      const stateType = event.dataTransfer.getData(
        'application/rsf-state-type',
      ) as StateType;
      if (!stateType) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const id = `${stateType}State${Date.now()}`;
      const newNode: FlowNode = {
        id,
        type: stateType,
        position,
        data: {
          label: id,
          stateType,
          stateData: { Type: stateType, End: true },
        } satisfies FlowNodeData,
      };

      addState(newNode);
      onGraphChange?.();
    },
    [screenToFlowPosition, addState, onGraphChange],
  );

  const handleNodesChange = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      onNodesChange(changes);
      // Trigger sync for position changes (drag) and removes
      const hasMeaningfulChange = changes.some(
        (c) =>
          c.type === 'position' && 'dragging' in c && c.dragging === false,
      );
      if (hasMeaningfulChange) {
        onGraphChange?.();
      }
    },
    [onNodesChange, onGraphChange],
  );

  const handleEdgesChange = useCallback(
    (changes: Parameters<typeof onEdgesChange>[0]) => {
      onEdgesChange(changes);
      const hasMeaningfulChange = changes.some(
        (c) => c.type === 'remove' || c.type === 'add',
      );
      if (hasMeaningfulChange) {
        onGraphChange?.();
      }
    },
    [onEdgesChange, onGraphChange],
  );

  const handleConnectEnd = useCallback(
    (...args: Parameters<typeof onConnect>) => {
      onConnect(...args);
      onGraphChange?.();
    },
    [onConnect, onGraphChange],
  );

  const handlePaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: { id: string }) => {
      if (selectedEdgeId === edge.id) {
        // Toggle off: re-clicking a selected edge deselects it
        selectEdge(null);
      } else {
        selectEdge(edge.id);
      }
    },
    [selectedEdgeId, selectEdge],
  );

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: { id: string }) => {
      selectNode(node.id);
    },
    [selectNode],
  );

  return (
    <div className="graph-pane">
      <div className="pane-header">Workflow Graph</div>
      <div
        className="graph-container"
        ref={containerRef}
        tabIndex={0}
      >
        {toastMessage && (
          <div className="graph-toast">{toastMessage}</div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={handleConnectEnd}
          onPaneClick={handlePaneClick}
          onEdgeClick={handleEdgeClick}
          onNodeClick={handleNodeClick}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
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
    </div>
  );
}
