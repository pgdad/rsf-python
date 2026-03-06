/**
 * Zustand flow store for the RSF graph editor.
 *
 * Manages nodes, edges, YAML content, validation errors, and sync state.
 * Uses immer for immutable state updates.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import {
  applyNodeChanges,
  applyEdgeChanges,
  type NodeChange,
  type EdgeChange,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react';
import type {
  FlowNode,
  FlowEdge,
  ValidationError,
  SyncSource,
} from '../types';

interface FlowState {
  nodes: FlowNode[];
  edges: FlowEdge[];
  yamlContent: string;
  validationErrors: ValidationError[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  toastMessage: string | null;
  syncSource: SyncSource;
  needsLayout: boolean;
  lastAst: Record<string, unknown> | null;

  // Actions
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  setNodes: (nodes: FlowNode[]) => void;
  setEdges: (edges: FlowEdge[]) => void;
  setYamlContent: (yaml: string) => void;
  setValidationErrors: (errors: ValidationError[]) => void;
  updateFromAst: (
    ast: Record<string, unknown>,
    errors: ValidationError[],
    nodes: FlowNode[],
    edges: FlowEdge[],
  ) => void;
  addState: (node: FlowNode) => void;
  removeState: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;
  removeEdge: (edgeId: string) => void;
  clearSelection: () => void;
  setToastMessage: (msg: string | null) => void;
  setSyncSource: (source: SyncSource) => void;
  setNeedsLayout: (needs: boolean) => void;
  setLastAst: (ast: Record<string, unknown> | null) => void;
}

export const useFlowStore = create<FlowState>()(
  immer((set) => ({
    nodes: [],
    edges: [],
    yamlContent: '',
    validationErrors: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    toastMessage: null,
    syncSource: null,
    needsLayout: false,
    lastAst: null,

    onNodesChange: (changes) =>
      set((state) => {
        const current = state.nodes as Node[];
        const updated = applyNodeChanges(changes, current);
        state.nodes = updated as unknown as FlowNode[];
      }),

    onEdgesChange: (changes) =>
      set((state) => {
        const current = state.edges as Edge[];
        const updated = applyEdgeChanges(changes, current);
        state.edges = updated as unknown as FlowEdge[];
      }),

    onConnect: (connection) =>
      set((state) => {
        const newEdge: FlowEdge = {
          id: `e-${connection.source}-${connection.target}`,
          source: connection.source!,
          target: connection.target!,
          type: 'transition',
          data: { edgeType: 'normal' },
        };
        state.edges.push(newEdge);
      }),

    setNodes: (nodes) => set({ nodes }),
    setEdges: (edges) => set({ edges }),
    setYamlContent: (yaml) => set({ yamlContent: yaml }),
    setValidationErrors: (errors) => set({ validationErrors: errors }),

    updateFromAst: (ast, errors, nodes, edges) =>
      set((state) => {
        state.lastAst = ast;
        state.validationErrors = errors;
        state.nodes = nodes;
        state.edges = edges;
      }),

    addState: (node) =>
      set((state) => {
        state.nodes.push(node);
        state.needsLayout = true;
      }),

    removeState: (nodeId) =>
      set((state) => {
        // Guard: cannot delete the last remaining node
        if (state.nodes.length <= 1) {
          state.toastMessage = 'Cannot delete the only state';
          return;
        }

        const nodeToRemove = state.nodes.find((n) => n.id === nodeId);
        const isStartNode = nodeToRemove?.data?.isStart === true;

        // Remove the node and all connected edges
        state.nodes = state.nodes.filter((n) => n.id !== nodeId);
        state.edges = state.edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId,
        );

        // Reassign isStart to alphabetically first remaining node if we deleted the start node
        if (isStartNode && state.nodes.length > 0) {
          const sorted = [...state.nodes].sort((a, b) =>
            a.id.localeCompare(b.id),
          );
          sorted[0].data.isStart = true;
        }

        // Clear selection state
        if (state.selectedNodeId === nodeId) {
          state.selectedNodeId = null;
        }
        state.selectedEdgeId = null;
      }),

    selectNode: (nodeId) =>
      set((state) => {
        state.selectedNodeId = nodeId;
        state.selectedEdgeId = null; // mutual exclusion
      }),

    selectEdge: (edgeId) =>
      set((state) => {
        state.selectedEdgeId = edgeId;
        state.selectedNodeId = null; // mutual exclusion
      }),

    removeEdge: (edgeId) =>
      set((state) => {
        const edge = state.edges.find((e) => e.id === edgeId);
        if (!edge) return;

        const edgeType = edge.data?.edgeType ?? 'normal';

        if (edgeType === 'catch') {
          state.toastMessage = 'Catch edges must be edited in YAML';
          return;
        }
        if (edgeType === 'choice') {
          state.toastMessage = 'Choice rule edges must be edited in YAML';
          return;
        }

        // Remove normal or default edges
        state.edges = state.edges.filter((e) => e.id !== edgeId);
        if (state.selectedEdgeId === edgeId) {
          state.selectedEdgeId = null;
        }
      }),

    clearSelection: () =>
      set((state) => {
        state.selectedNodeId = null;
        state.selectedEdgeId = null;
      }),

    setToastMessage: (msg) => set({ toastMessage: msg }),
    setSyncSource: (source) => set({ syncSource: source }),
    setNeedsLayout: (needs) => set({ needsLayout: needs }),
    setLastAst: (ast) => set({ lastAst: ast }),
  })),
);
