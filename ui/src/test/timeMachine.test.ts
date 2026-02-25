import { describe, it, expect } from 'vitest';
import { buildSnapshots } from '../inspector/timeMachine';
import type { InspectNode, InspectEdge } from '../store/inspectStore';
import type { HistoryEvent } from '../inspector/types';

function makeNode(id: string): InspectNode {
  return {
    id,
    position: { x: 0, y: 0 },
    data: { label: id, stateType: 'Task' },
  };
}

function makeEdge(source: string, target: string): InspectEdge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
  };
}

function makeEvent(
  eventId: number,
  eventType: string,
  stateName: string,
  timestamp: string,
  extra: Record<string, unknown> = {},
): HistoryEvent {
  return {
    event_id: eventId,
    timestamp,
    event_type: eventType,
    sub_type: null,
    details: { stateName, ...extra },
  };
}

describe('buildSnapshots', () => {
  it('returns an empty array when events are empty', () => {
    const nodes = [makeNode('A')];
    const result = buildSnapshots([], nodes, []);
    expect(result).toEqual([]);
  });

  it('returns an empty array when nodes are empty', () => {
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
    ];
    const result = buildSnapshots(events, [], []);
    expect(result).toEqual([]);
  });

  it('produces one snapshot per event', () => {
    const nodes = [makeNode('A'), makeNode('B')];
    const edges = [makeEdge('A', 'B')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:01Z'),
      makeEvent(3, 'StateStarted', 'B', '2025-01-01T00:00:02Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, edges);
    expect(snapshots).toHaveLength(3);
  });

  it('sets node status to running on a started event', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[0].nodeOverlays['A'].status).toBe('running');
    expect(snapshots[0].nodeOverlays['A'].enteredAt).toBe('2025-01-01T00:00:00Z');
  });

  it('sets node status to succeeded on a succeeded event', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:05Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[1].nodeOverlays['A'].status).toBe('succeeded');
    expect(snapshots[1].nodeOverlays['A'].exitedAt).toBe('2025-01-01T00:00:05Z');
    expect(snapshots[1].nodeOverlays['A'].durationMs).toBe(5000);
  });

  it('sets node status to failed on a failed event', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateFailed', 'A', '2025-01-01T00:00:03Z', {
        error: 'SomeError',
      }),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[1].nodeOverlays['A'].status).toBe('failed');
    expect(snapshots[1].nodeOverlays['A'].error).toBe('SomeError');
  });

  it('marks edges as traversed when transitioning between states', () => {
    const nodes = [makeNode('A'), makeNode('B')];
    const edges = [makeEdge('A', 'B')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:01Z'),
      makeEvent(3, 'StateStarted', 'B', '2025-01-01T00:00:02Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, edges);

    // After event 0 and 1, edge should not be traversed yet
    expect(snapshots[0].edgeOverlays['e-A-B'].traversed).toBe(false);
    expect(snapshots[1].edgeOverlays['e-A-B'].traversed).toBe(false);

    // After event 2 (B started), edge A->B should be traversed
    expect(snapshots[2].edgeOverlays['e-A-B'].traversed).toBe(true);
    expect(snapshots[2].edgeOverlays['e-A-B'].timestamp).toBe('2025-01-01T00:00:02Z');
  });

  it('captures input and output from event details', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z', {
        input: '{"key":"value"}',
      }),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:01Z', {
        output: { result: 42 },
      }),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[0].nodeOverlays['A'].input).toEqual({ key: 'value' });
    expect(snapshots[1].nodeOverlays['A'].output).toEqual({ result: 42 });
  });

  it('each snapshot is an independent copy of state', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:01Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, []);

    // Snapshot 0 should still show running even after snapshot 1 shows succeeded
    expect(snapshots[0].nodeOverlays['A'].status).toBe('running');
    expect(snapshots[1].nodeOverlays['A'].status).toBe('succeeded');
  });

  it('handles events for unknown nodes gracefully', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'Unknown', '2025-01-01T00:00:00Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots).toHaveLength(1);
    // Node A should still be pending since the event was for an unknown node
    expect(snapshots[0].nodeOverlays['A'].status).toBe('pending');
  });

  it('detects state name from alternative detail fields', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      {
        event_id: 1,
        timestamp: '2025-01-01T00:00:00Z',
        event_type: 'StateStarted',
        sub_type: null,
        details: { Name: 'A' },
      },
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[0].nodeOverlays['A'].status).toBe('running');
  });

  it('records eventIndex and timestamp on each snapshot', () => {
    const nodes = [makeNode('A')];
    const events: HistoryEvent[] = [
      makeEvent(1, 'StateStarted', 'A', '2025-01-01T00:00:00Z'),
      makeEvent(2, 'StateSucceeded', 'A', '2025-01-01T00:00:05Z'),
    ];

    const snapshots = buildSnapshots(events, nodes, []);
    expect(snapshots[0].eventIndex).toBe(0);
    expect(snapshots[0].timestamp).toBe('2025-01-01T00:00:00Z');
    expect(snapshots[1].eventIndex).toBe(1);
    expect(snapshots[1].timestamp).toBe('2025-01-01T00:00:05Z');
  });
});
