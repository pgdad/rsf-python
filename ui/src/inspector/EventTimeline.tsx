/**
 * EventTimeline - Vertical timeline of execution history events.
 *
 * Features:
 * - Vertical timeline with event markers
 * - Click to select event (updates time machine scrubber)
 * - Color-coded by event type (started/succeeded/failed)
 * - Shows timestamp and state name
 */

import { useCallback } from 'react';
import { useInspectStore } from '../store/inspectStore';
import type { HistoryEvent, NodeOverlayStatus } from './types';

const EVENT_COLORS: Record<string, string> = {
  running: '#3498db',
  succeeded: '#27ae60',
  failed: '#e74c3c',
  caught: '#e6a817',
  pending: '#666666',
};

function classifyEvent(event: HistoryEvent): NodeOverlayStatus {
  const t = event.event_type.toLowerCase();
  const st = (event.sub_type || '').toLowerCase();
  if (t.includes('succeeded') || t.includes('completed') || st.includes('succeeded')) return 'succeeded';
  if (t.includes('failed') || st.includes('failed')) return 'failed';
  if (t.includes('caught') || st.includes('caught')) return 'caught';
  if (t.includes('started') || t.includes('enter') || st.includes('started')) return 'running';
  return 'pending';
}

function getEventLabel(event: HistoryEvent): string {
  const details = event.details;
  const name =
    (details.stateName as string) ||
    (details.StateName as string) ||
    (details.name as string) ||
    (details.Name as string) ||
    '';
  if (name) return name;
  return event.event_type;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function EventTimeline() {
  const events = useInspectStore((s) => s.events);
  const playbackIndex = useInspectStore((s) => s.playbackIndex);
  const setPlaybackIndex = useInspectStore((s) => s.setPlaybackIndex);
  const setIsLive = useInspectStore((s) => s.setIsLive);
  const executionDetail = useInspectStore((s) => s.executionDetail);

  const handleEventClick = useCallback(
    (index: number) => {
      setPlaybackIndex(index);
      setIsLive(false);
    },
    [setPlaybackIndex, setIsLive],
  );

  if (!executionDetail) {
    return (
      <div className="event-timeline">
        <div className="pane-header">Timeline</div>
        <div className="timeline-empty">Select an execution to view timeline</div>
      </div>
    );
  }

  return (
    <div className="event-timeline">
      <div className="pane-header">
        Timeline ({events.length} events)
      </div>
      <div className="timeline-events">
        {events.map((event, idx) => {
          const status = classifyEvent(event);
          const color = EVENT_COLORS[status];
          const isActive = idx === playbackIndex;

          return (
            <div
              key={event.event_id}
              className={`timeline-event ${isActive ? 'active' : ''}`}
              onClick={() => handleEventClick(idx)}
            >
              <div className="timeline-track">
                <div
                  className="timeline-dot"
                  style={{ backgroundColor: color }}
                />
                {idx < events.length - 1 && (
                  <div className="timeline-line" />
                )}
              </div>
              <div className="timeline-event-content">
                <div className="timeline-event-header">
                  <span className="timeline-event-name" style={{ color }}>
                    {getEventLabel(event)}
                  </span>
                  <span className="timeline-event-time">
                    {formatTime(event.timestamp)}
                  </span>
                </div>
                <div className="timeline-event-type">
                  {event.event_type}
                  {event.sub_type ? ` / ${event.sub_type}` : ''}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
