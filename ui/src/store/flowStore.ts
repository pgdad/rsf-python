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
        state.nodes = state.nodes.filter((n) => n.id !== nodeId);
        state.edges = state.edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId,
        );
        if (state.selectedNodeId === nodeId) {
          state.selectedNodeId = null;
        }
      }),

    selectNode: (nodeId) => set({ selectedNodeId: nodeId }),
    setSyncSource: (source) => set({ syncSource: source }),
    setNeedsLayout: (needs) => set({ needsLayout: needs }),
    setLastAst: (ast) => set({ lastAst: ast }),
  })),
);
