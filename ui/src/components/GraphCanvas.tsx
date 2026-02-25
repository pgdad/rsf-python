/**
 * Graph canvas component using @xyflow/react.
 * Renders the workflow graph with minimap, controls, and background grid.
 * Supports drag-drop from palette.
 */

import { useCallback, type DragEvent } from 'react';
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

  const { screenToFlowPosition } = useReactFlow();

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
    selectNode(null);
  }, [selectNode]);

  return (
    <div className="graph-pane">
      <div className="pane-header">Workflow Graph</div>
      <div className="graph-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={handleConnectEnd}
          onPaneClick={handlePaneClick}
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
