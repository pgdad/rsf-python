/**
 * Zustand inspect store for the RSF Execution Inspector.
 *
 * Manages execution list, selected execution, history events,
 * graph nodes/edges with overlays, and time machine playback state.
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Node, Edge } from '@xyflow/react';
import type {
  ExecutionSummary,
  ExecutionDetail,
  ExecutionStatus,
  HistoryEvent,
  NodeOverlay,
  EdgeOverlay,
  TransitionSnapshot,
  StatusFilter,
} from '../inspector/types';

/** Inspector graph node */
export interface InspectNode extends Node {
  data: {
    label: string;
    stateType: string;
    isStart?: boolean;
    overlay?: NodeOverlay;
    [key: string]: unknown;
  };
}

/** Inspector graph edge */
export interface InspectEdge extends Edge {
  data?: {
    overlay?: EdgeOverlay;
    edgeType?: string;
    label?: string;
    [key: string]: unknown;
  };
}

interface InspectState {
  // Execution list
  functionName: string;
  executions: ExecutionSummary[];
  nextToken: string | null;
  statusFilter: StatusFilter;
  searchQuery: string;
  loading: boolean;

  // Selected execution
  selectedExecutionId: string | null;
  executionDetail: Omit<ExecutionDetail, 'history'> | null;
  events: HistoryEvent[];

  // Graph state
  nodes: InspectNode[];
  edges: InspectEdge[];
  nodeOverlays: Record<string, NodeOverlay>;
  edgeOverlays: Record<string, EdgeOverlay>;

  // Time machine
  snapshots: TransitionSnapshot[];
  playbackIndex: number;
  isLive: boolean;

  // Selected state for detail panel
  selectedNodeId: string | null;

  // Actions
  setFunctionName: (name: string) => void;
  setExecutions: (executions: ExecutionSummary[], nextToken: string | null) => void;
  appendExecutions: (executions: ExecutionSummary[], nextToken: string | null) => void;
  setStatusFilter: (filter: StatusFilter) => void;
  setSearchQuery: (query: string) => void;
  setLoading: (loading: boolean) => void;

  selectExecution: (id: string | null) => void;
  setExecutionDetail: (detail: Omit<ExecutionDetail, 'history'>) => void;
  setEvents: (events: HistoryEvent[]) => void;
  appendEvents: (events: HistoryEvent[]) => void;

  setGraphElements: (nodes: InspectNode[], edges: InspectEdge[]) => void;
  setNodeOverlays: (overlays: Record<string, NodeOverlay>) => void;
  setEdgeOverlays: (overlays: Record<string, EdgeOverlay>) => void;

  setSnapshots: (snapshots: TransitionSnapshot[]) => void;
  setPlaybackIndex: (index: number) => void;
  setIsLive: (live: boolean) => void;

  selectNode: (nodeId: string | null) => void;

  reset: () => void;
}

const initialState = {
  functionName: '',
  executions: [],
  nextToken: null,
  statusFilter: 'ALL' as StatusFilter,
  searchQuery: '',
  loading: false,
  selectedExecutionId: null,
  executionDetail: null,
  events: [],
  nodes: [],
  edges: [],
  nodeOverlays: {},
  edgeOverlays: {},
  snapshots: [],
  playbackIndex: -1,
  isLive: true,
  selectedNodeId: null,
};

export const useInspectStore = create<InspectState>()(
  immer((set) => ({
    ...initialState,

    setFunctionName: (name) => set({ functionName: name }),

    setExecutions: (executions, nextToken) =>
      set({ executions, nextToken }),

    appendExecutions: (executions, nextToken) =>
      set((state) => {
        state.executions.push(...executions);
        state.nextToken = nextToken;
      }),

    setStatusFilter: (filter) => set({ statusFilter: filter }),
    setSearchQuery: (query) => set({ searchQuery: query }),
    setLoading: (loading) => set({ loading }),

    selectExecution: (id) =>
      set((state) => {
        state.selectedExecutionId = id;
        state.executionDetail = null;
        state.events = [];
        state.snapshots = [];
        state.playbackIndex = -1;
        state.isLive = true;
        state.nodeOverlays = {};
        state.edgeOverlays = {};
        state.selectedNodeId = null;
      }),

    setExecutionDetail: (detail) => set({ executionDetail: detail }),

    setEvents: (events) => set({ events }),

    appendEvents: (events) =>
      set((state) => {
        state.events.push(...events);
      }),

    setGraphElements: (nodes, edges) => set({ nodes, edges }),

    setNodeOverlays: (overlays) => set({ nodeOverlays: overlays }),
    setEdgeOverlays: (overlays) => set({ edgeOverlays: overlays }),

    setSnapshots: (snapshots) => set({ snapshots }),
    setPlaybackIndex: (index) => set({ playbackIndex: index }),
    setIsLive: (live) => set({ isLive: live }),

    selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

    reset: () => set(initialState),
  })),
);
