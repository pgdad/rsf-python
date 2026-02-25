/**
 * Time machine - Precomputed TransitionSnapshots for O(1) scrubbing.
 *
 * Given a list of history events, precomputes a snapshot at each event
 * representing the full graph state (all node and edge overlays) at that
 * point in time. The TimelineScrubber indexes into this array for instant
 * rendering without recomputation.
 */

import type { InspectNode, InspectEdge } from '../store/inspectStore';
import type {
  HistoryEvent,
  TransitionSnapshot,
  NodeOverlay,
  EdgeOverlay,
  NodeOverlayStatus,
} from './types';

/** Default node overlay (pending, no data) */
function defaultNodeOverlay(): NodeOverlay {
  return {
    status: 'pending',
    enteredAt: null,
    exitedAt: null,
    durationMs: null,
    input: null,
    output: null,
    error: null,
    retryAttempt: 0,
  };
}

/** Default edge overlay (not traversed) */
function defaultEdgeOverlay(): EdgeOverlay {
  return {
    traversed: false,
    timestamp: null,
  };
}

/**
 * Extract the state name from a history event.
 *
 * History events from Lambda durable executions include state info
 * in the details object. We look for common patterns.
 */
function getStateName(event: HistoryEvent): string | null {
  const d = event.details;
  if (d.stateName && typeof d.stateName === 'string') return d.stateName;
  if (d.StateName && typeof d.StateName === 'string') return d.StateName;
  if (d.state_name && typeof d.state_name === 'string') return d.state_name;
  if (d.name && typeof d.name === 'string') return d.name;
  if (d.Name && typeof d.Name === 'string') return d.Name;
  return null;
}

/**
 * Map an event type + sub_type to a node overlay status.
 */
function eventToStatus(event: HistoryEvent): NodeOverlayStatus | null {
  const t = event.event_type.toLowerCase();
  const st = (event.sub_type || '').toLowerCase();

  if (t.includes('started') || t.includes('enter') || st.includes('started') || st.includes('enter')) {
    return 'running';
  }
  if (t.includes('succeeded') || t.includes('completed') || st.includes('succeeded') || st.includes('completed')) {
    return 'succeeded';
  }
  if (t.includes('failed') || st.includes('failed')) {
    return 'failed';
  }
  if (t.includes('caught') || st.includes('caught')) {
    return 'caught';
  }
  if (t.includes('retri') || st.includes('retri')) {
    return 'running'; // retrying = still running
  }
  return null;
}

/**
 * Build an array of TransitionSnapshots from history events.
 *
 * Each snapshot represents the complete graph state after processing
 * the event at that index. The playback slider indexes directly into
 * this array for O(1) lookup.
 */
export function buildSnapshots(
  events: HistoryEvent[],
  nodes: InspectNode[],
  edges: InspectEdge[],
): TransitionSnapshot[] {
  if (events.length === 0 || nodes.length === 0) return [];

  // Initialize mutable overlay state
  const nodeState: Record<string, NodeOverlay> = {};
  for (const node of nodes) {
    nodeState[node.id] = defaultNodeOverlay();
  }
  const edgeState: Record<string, EdgeOverlay> = {};
  for (const edge of edges) {
    edgeState[edge.id] = defaultEdgeOverlay();
  }

  // Build edge lookup: source -> target -> edgeId
  const edgeLookup: Record<string, Record<string, string>> = {};
  for (const edge of edges) {
    if (!edgeLookup[edge.source]) edgeLookup[edge.source] = {};
    edgeLookup[edge.source][edge.target] = edge.id;
  }

  // Track the previous state name for edge traversal detection
  let prevStateName: string | null = null;

  const snapshots: TransitionSnapshot[] = [];

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const stateName = getStateName(event);
    const status = eventToStatus(event);

    if (stateName && nodeState[stateName]) {
      const overlay = nodeState[stateName];

      if (status) {
        overlay.status = status;
      }

      if (status === 'running' && !overlay.enteredAt) {
        overlay.enteredAt = event.timestamp;
      }

      if (status === 'succeeded' || status === 'failed' || status === 'caught') {
        overlay.exitedAt = event.timestamp;
        if (overlay.enteredAt) {
          overlay.durationMs =
            new Date(event.timestamp).getTime() -
            new Date(overlay.enteredAt).getTime();
        }
      }

      // Extract I/O data from event details
      if (event.details.input) {
        overlay.input = typeof event.details.input === 'string'
          ? tryParseJson(event.details.input)
          : event.details.input as Record<string, unknown>;
      }
      if (event.details.output) {
        overlay.output = typeof event.details.output === 'string'
          ? tryParseJson(event.details.output)
          : event.details.output as Record<string, unknown>;
      }
      if (event.details.error) {
        overlay.error = typeof event.details.error === 'string'
          ? event.details.error
          : JSON.stringify(event.details.error);
      }
      if (event.details.retryAttempt !== undefined) {
        overlay.retryAttempt = Number(event.details.retryAttempt);
      }

      // Mark edge as traversed when transitioning between states
      if (prevStateName && prevStateName !== stateName && status === 'running') {
        const edgeId = edgeLookup[prevStateName]?.[stateName];
        if (edgeId && edgeState[edgeId]) {
          edgeState[edgeId].traversed = true;
          edgeState[edgeId].timestamp = event.timestamp;
        }
      }

      if (status === 'running') {
        prevStateName = stateName;
      }
    }

    // Create a deep clone of current state as the snapshot
    const snapNodeOverlays: Record<string, NodeOverlay> = {};
    for (const [k, v] of Object.entries(nodeState)) {
      snapNodeOverlays[k] = { ...v };
    }
    const snapEdgeOverlays: Record<string, EdgeOverlay> = {};
    for (const [k, v] of Object.entries(edgeState)) {
      snapEdgeOverlays[k] = { ...v };
    }

    snapshots.push({
      eventIndex: i,
      timestamp: event.timestamp,
      nodeOverlays: snapNodeOverlays,
      edgeOverlays: snapEdgeOverlays,
    });
  }

  return snapshots;
}

function tryParseJson(value: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === 'object' && parsed !== null ? parsed : { value: parsed };
  } catch {
    return { raw: value };
  }
}
