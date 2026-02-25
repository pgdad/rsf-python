import { describe, it, expect, beforeEach } from 'vitest';
import { useInspectStore } from '../store/inspectStore';
import type { ExecutionSummary } from '../inspector/types';

/**
 * Helper to reset the store to initial state between tests.
 * Since zustand stores are singletons, we must reset manually.
 */
function resetStore() {
  useInspectStore.getState().reset();
}

describe('useInspectStore', () => {
  beforeEach(() => {
    resetStore();
  });

  describe('initial state', () => {
    it('has correct default values', () => {
      const state = useInspectStore.getState();
      expect(state.functionName).toBe('');
      expect(state.executions).toEqual([]);
      expect(state.nextToken).toBeNull();
      expect(state.statusFilter).toBe('ALL');
      expect(state.searchQuery).toBe('');
      expect(state.loading).toBe(false);
      expect(state.selectedExecutionId).toBeNull();
      expect(state.executionDetail).toBeNull();
      expect(state.events).toEqual([]);
      expect(state.nodes).toEqual([]);
      expect(state.edges).toEqual([]);
      expect(state.nodeOverlays).toEqual({});
      expect(state.edgeOverlays).toEqual({});
      expect(state.snapshots).toEqual([]);
      expect(state.playbackIndex).toBe(-1);
      expect(state.isLive).toBe(true);
      expect(state.selectedNodeId).toBeNull();
    });
  });

  describe('setExecutions', () => {
    it('sets executions and nextToken', () => {
      const mockExecutions: ExecutionSummary[] = [
        {
          execution_id: 'exec-1',
          name: 'test-exec',
          status: 'RUNNING',
          function_name: 'myFunc',
          start_time: '2025-01-01T00:00:00Z',
          end_time: null,
        },
      ];

      useInspectStore.getState().setExecutions(mockExecutions, 'token-abc');

      const state = useInspectStore.getState();
      expect(state.executions).toHaveLength(1);
      expect(state.executions[0].execution_id).toBe('exec-1');
      expect(state.nextToken).toBe('token-abc');
    });

    it('replaces existing executions', () => {
      const exec1: ExecutionSummary[] = [
        {
          execution_id: 'exec-1',
          name: 'first',
          status: 'RUNNING',
          function_name: 'myFunc',
          start_time: '2025-01-01T00:00:00Z',
          end_time: null,
        },
      ];
      const exec2: ExecutionSummary[] = [
        {
          execution_id: 'exec-2',
          name: 'second',
          status: 'SUCCEEDED',
          function_name: 'myFunc',
          start_time: '2025-01-01T00:01:00Z',
          end_time: '2025-01-01T00:02:00Z',
        },
      ];

      useInspectStore.getState().setExecutions(exec1, null);
      useInspectStore.getState().setExecutions(exec2, null);

      const state = useInspectStore.getState();
      expect(state.executions).toHaveLength(1);
      expect(state.executions[0].execution_id).toBe('exec-2');
    });
  });

  describe('appendExecutions', () => {
    it('appends to existing executions', () => {
      const exec1: ExecutionSummary[] = [
        {
          execution_id: 'exec-1',
          name: 'first',
          status: 'RUNNING',
          function_name: 'myFunc',
          start_time: '2025-01-01T00:00:00Z',
          end_time: null,
        },
      ];
      const exec2: ExecutionSummary[] = [
        {
          execution_id: 'exec-2',
          name: 'second',
          status: 'SUCCEEDED',
          function_name: 'myFunc',
          start_time: '2025-01-01T00:01:00Z',
          end_time: '2025-01-01T00:02:00Z',
        },
      ];

      useInspectStore.getState().setExecutions(exec1, 'token-1');
      useInspectStore.getState().appendExecutions(exec2, null);

      const state = useInspectStore.getState();
      expect(state.executions).toHaveLength(2);
      expect(state.executions[0].execution_id).toBe('exec-1');
      expect(state.executions[1].execution_id).toBe('exec-2');
      expect(state.nextToken).toBeNull();
    });
  });

  describe('selectExecution', () => {
    it('sets selectedExecutionId and resets related state', () => {
      // Pre-populate some state that should be reset
      useInspectStore.getState().setEvents([
        {
          event_id: 1,
          timestamp: '2025-01-01T00:00:00Z',
          event_type: 'test',
          sub_type: null,
          details: {},
        },
      ]);
      useInspectStore.getState().setPlaybackIndex(5);
      useInspectStore.getState().setIsLive(false);
      useInspectStore.getState().selectNode('some-node');

      // Select an execution
      useInspectStore.getState().selectExecution('exec-123');

      const state = useInspectStore.getState();
      expect(state.selectedExecutionId).toBe('exec-123');
      expect(state.executionDetail).toBeNull();
      expect(state.events).toEqual([]);
      expect(state.snapshots).toEqual([]);
      expect(state.playbackIndex).toBe(-1);
      expect(state.isLive).toBe(true);
      expect(state.nodeOverlays).toEqual({});
      expect(state.edgeOverlays).toEqual({});
      expect(state.selectedNodeId).toBeNull();
    });

    it('can deselect by passing null', () => {
      useInspectStore.getState().selectExecution('exec-123');
      useInspectStore.getState().selectExecution(null);

      expect(useInspectStore.getState().selectedExecutionId).toBeNull();
    });
  });

  describe('playback controls', () => {
    it('setPlaybackIndex updates the index', () => {
      useInspectStore.getState().setPlaybackIndex(3);
      expect(useInspectStore.getState().playbackIndex).toBe(3);
    });

    it('setIsLive toggles live mode', () => {
      expect(useInspectStore.getState().isLive).toBe(true);
      useInspectStore.getState().setIsLive(false);
      expect(useInspectStore.getState().isLive).toBe(false);
    });
  });

  describe('setFunctionName', () => {
    it('updates the function name', () => {
      useInspectStore.getState().setFunctionName('my-state-machine');
      expect(useInspectStore.getState().functionName).toBe('my-state-machine');
    });
  });

  describe('setStatusFilter', () => {
    it('updates the status filter', () => {
      useInspectStore.getState().setStatusFilter('FAILED');
      expect(useInspectStore.getState().statusFilter).toBe('FAILED');
    });
  });

  describe('setLoading', () => {
    it('updates loading state', () => {
      useInspectStore.getState().setLoading(true);
      expect(useInspectStore.getState().loading).toBe(true);
      useInspectStore.getState().setLoading(false);
      expect(useInspectStore.getState().loading).toBe(false);
    });
  });

  describe('selectNode', () => {
    it('sets the selected node id', () => {
      useInspectStore.getState().selectNode('node-A');
      expect(useInspectStore.getState().selectedNodeId).toBe('node-A');
    });

    it('clears selection with null', () => {
      useInspectStore.getState().selectNode('node-A');
      useInspectStore.getState().selectNode(null);
      expect(useInspectStore.getState().selectedNodeId).toBeNull();
    });
  });

  describe('reset', () => {
    it('restores the store to its initial state', () => {
      // Mutate several fields
      useInspectStore.getState().setFunctionName('changed');
      useInspectStore.getState().setLoading(true);
      useInspectStore.getState().setPlaybackIndex(10);
      useInspectStore.getState().setIsLive(false);

      // Reset
      useInspectStore.getState().reset();

      const state = useInspectStore.getState();
      expect(state.functionName).toBe('');
      expect(state.loading).toBe(false);
      expect(state.playbackIndex).toBe(-1);
      expect(state.isLive).toBe(true);
    });
  });
});
