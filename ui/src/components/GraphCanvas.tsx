/**
 * Graph canvas component using @xyflow/react.
 * Renders the workflow graph with minimap, controls, and background grid.
 * Supports drag-drop from palette, edge selection/deletion, and keyboard shortcuts.
 * Includes custom scroll bars overlaying the canvas for large graph navigation.
 */

import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useReactFlow,
  useViewport,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useFlowStore } from '../store/flowStore';
import { nodeTypes } from '../nodes';
import { edgeTypes } from '../edges';
import type { FlowNode, StateType, FlowNodeData } from '../types';

interface GraphCanvasProps {
  onGraphChange?: () => void;
}

// Padding around the bounding box of all nodes (in flow-space units)
const BOUNDING_PAD = 200;

/**
 * GraphScrollBars renders two thin custom scroll bars (horizontal + vertical)
 * that stay in sync with the React Flow viewport transform. It reads current
 * viewport state via useViewport() and updates it via setViewport().
 *
 * The scroll bars are absolutely-positioned inside .graph-container and use
 * opacity transitions to auto-hide after 2 seconds of inactivity.
 */
function GraphScrollBars({ containerRef }: { containerRef: React.RefObject<HTMLDivElement | null> }) {
  const { x, y, zoom } = useViewport();
  const { setViewport, getNodes } = useReactFlow();

  // Visibility state: 'visible' or 'hidden'
  const [visible, setVisible] = useState(false);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Container dimensions (updated on resize)
  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 });

  // Dragging state
  const draggingRef = useRef<{
    axis: 'x' | 'y';
    startPointer: number;
    startViewport: number;
    extent: number;
    containerDim: number;
  } | null>(null);

  // Observe container size
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) {
        setContainerSize({ width: e.contentRect.width, height: e.contentRect.height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [containerRef]);

  // Show scroll bars and reset auto-hide timer whenever viewport changes
  useEffect(() => {
    setVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    hideTimerRef.current = setTimeout(() => setVisible(false), 2000);
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [x, y, zoom]);

  const showScrollBars = useCallback(() => {
    setVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    hideTimerRef.current = setTimeout(() => setVisible(false), 2000);
  }, []);

  // Compute bounding box of all nodes in flow-space
  const nodes = getNodes();
  if (nodes.length === 0) return null;

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const node of nodes) {
    const nx = node.position.x;
    const ny = node.position.y;
    const nw = (node.measured?.width ?? node.width ?? 160);
    const nh = (node.measured?.height ?? node.height ?? 60);
    if (nx < minX) minX = nx;
    if (ny < minY) minY = ny;
    if (nx + nw > maxX) maxX = nx + nw;
    if (ny + nh > maxY) maxY = ny + nh;
  }

  // Add padding
  minX -= BOUNDING_PAD;
  minY -= BOUNDING_PAD;
  maxX += BOUNDING_PAD;
  maxY += BOUNDING_PAD;

  // Total extent in screen-space pixels
  const extentW = (maxX - minX) * zoom;
  const extentH = (maxY - minY) * zoom;

  const { width: cw, height: ch } = containerSize;

  // Thumb sizes as fraction of container vs extent (clamped 0.05..0.99)
  const hThumbRatio = Math.min(0.99, Math.max(0.05, cw / Math.max(extentW, cw)));
  const vThumbRatio = Math.min(0.99, Math.max(0.05, ch / Math.max(extentH, ch)));

  // Thumb sizes in pixels (track is cw/ch minus the 10px corner gap)
  const TRACK_SIZE = 10; // px
  const CORNER_GAP = TRACK_SIZE;
  const hTrackW = cw - CORNER_GAP;
  const vTrackH = ch - CORNER_GAP;
  const hThumbW = hThumbRatio * hTrackW;
  const vThumbH = vThumbRatio * vTrackH;

  // Current scroll position as fraction (0=start, 1=end)
  // viewport x = -minX*zoom + offset => offset = x + minX*zoom
  // scrollFraction = offset / (extentW - cw) clamped [0,1]
  const hScrollRange = Math.max(0, extentW - cw);
  const vScrollRange = Math.max(0, extentH - ch);

  const hOffset = x + minX * zoom;
  const vOffset = y + minY * zoom;

  const hFrac = hScrollRange > 0 ? Math.min(1, Math.max(0, -hOffset / hScrollRange)) : 0;
  const vFrac = vScrollRange > 0 ? Math.min(1, Math.max(0, -vOffset / vScrollRange)) : 0;

  // Thumb positions within the track
  const hThumbX = hFrac * (hTrackW - hThumbW);
  const vThumbY = vFrac * (vTrackH - vThumbH);

  // Mouse drag start handler
  const startDrag = (axis: 'x' | 'y', e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const startPointer = axis === 'x' ? e.clientX : e.clientY;
    const startViewport = axis === 'x' ? x : y;
    const extent = axis === 'x' ? hScrollRange : vScrollRange;
    const containerDim = axis === 'x' ? hTrackW - hThumbW : vTrackH - vThumbH;

    draggingRef.current = { axis, startPointer, startViewport, extent, containerDim };

    const onMouseMove = (me: MouseEvent) => {
      if (!draggingRef.current) return;
      const { axis: a, startPointer: sp, startViewport: sv, extent: ext, containerDim: cd } = draggingRef.current;
      const delta = (a === 'x' ? me.clientX : me.clientY) - sp;
      const fracDelta = cd > 0 ? delta / cd : 0;
      const newOffset = -(fracDelta * ext);
      requestAnimationFrame(() => {
        if (a === 'x') {
          setViewport({ x: sv + newOffset, y, zoom });
        } else {
          setViewport({ x, y: sv + newOffset, zoom });
        }
      });
    };

    const onMouseUp = () => {
      draggingRef.current = null;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  // Click on track (not thumb) to jump viewport
  const handleTrackClick = (axis: 'x' | 'y', e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (axis === 'x') {
      const clickPos = e.clientX - rect.left;
      const frac = Math.min(1, Math.max(0, (clickPos - hThumbW / 2) / (hTrackW - hThumbW)));
      setViewport({ x: -(frac * hScrollRange) - minX * zoom, y, zoom });
    } else {
      const clickPos = e.clientY - rect.top;
      const frac = Math.min(1, Math.max(0, (clickPos - vThumbH / 2) / (vTrackH - vThumbH)));
      setViewport({ x, y: -(frac * vScrollRange) - minY * zoom, zoom });
    }
    showScrollBars();
  };

  const opacity = visible ? 1 : 0;

  return (
    <>
      {/* Horizontal scroll bar */}
      <div
        className="graph-scrollbar-track graph-scrollbar-horizontal"
        style={{
          position: 'absolute',
          bottom: TRACK_SIZE,
          left: 0,
          width: hTrackW,
          height: TRACK_SIZE,
          zIndex: 4,
          opacity,
          transition: 'opacity 0.3s',
          cursor: 'pointer',
        }}
        onMouseEnter={showScrollBars}
        onClick={handleTrackClick.bind(null, 'x')}
      >
        <div
          className="graph-scrollbar-thumb graph-scrollbar-thumb-horizontal"
          style={{
            position: 'absolute',
            left: hThumbX,
            top: 1,
            width: hThumbW,
            height: TRACK_SIZE - 2,
            borderRadius: 5,
            cursor: 'grab',
          }}
          onMouseDown={(e) => startDrag('x', e)}
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Vertical scroll bar */}
      <div
        className="graph-scrollbar-track graph-scrollbar-vertical"
        style={{
          position: 'absolute',
          top: 0,
          right: TRACK_SIZE,
          width: TRACK_SIZE,
          height: vTrackH,
          zIndex: 4,
          opacity,
          transition: 'opacity 0.3s',
          cursor: 'pointer',
        }}
        onMouseEnter={showScrollBars}
        onClick={handleTrackClick.bind(null, 'y')}
      >
        <div
          className="graph-scrollbar-thumb graph-scrollbar-thumb-vertical"
          style={{
            position: 'absolute',
            top: vThumbY,
            left: 1,
            width: TRACK_SIZE - 2,
            height: vThumbH,
            borderRadius: 5,
            cursor: 'grab',
          }}
          onMouseDown={(e) => startDrag('y', e)}
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Corner filler */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: TRACK_SIZE * 2,
          height: TRACK_SIZE * 2,
          zIndex: 4,
          opacity,
          transition: 'opacity 0.3s',
        }}
      />
    </>
  );
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
  const removeState = useFlowStore((s) => s.removeState);
  const clearSelection = useFlowStore((s) => s.clearSelection);
  const selectedEdgeId = useFlowStore((s) => s.selectedEdgeId);
  const toastMessage = useFlowStore((s) => s.toastMessage);
  const setToastMessage = useFlowStore((s) => s.setToastMessage);

  const containerRef = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // Listen for property changes dispatched by node components (bridge to sync pipeline)
  useEffect(() => {
    const handlePropertyChange = () => {
      onGraphChange?.();
    };
    document.addEventListener('rsf-graph-change', handlePropertyChange);
    return () => document.removeEventListener('rsf-graph-change', handlePropertyChange);
  }, [onGraphChange]);

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
        const currentSelectedNodeId = useFlowStore.getState().selectedNodeId;
        if (currentSelectedEdgeId) {
          event.preventDefault();
          removeEdge(currentSelectedEdgeId);
          onGraphChange?.();
        } else if (currentSelectedNodeId) {
          event.preventDefault();
          removeState(currentSelectedNodeId);
          onGraphChange?.();
        }
      } else if (event.key === 'Escape') {
        clearSelection();
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [removeEdge, removeState, clearSelection, onGraphChange]);

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
        <GraphScrollBars containerRef={containerRef} />
      </div>
    </div>
  );
}
