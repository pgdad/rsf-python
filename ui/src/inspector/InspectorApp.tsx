/**
 * Inspector App - Three-panel layout for execution inspection.
 *
 * Layout: ExecutionList (left) | InspectorGraph + Header (center) | EventTimeline + StateDetail (right)
 */

import { useCallback } from 'react';
import { useInspectStore } from '../store/inspectStore';
import { useSSE } from './useSSE';
import { ExecutionList } from './ExecutionList';
import { ExecutionHeader } from './ExecutionHeader';
import { InspectorGraph } from './InspectorGraph';
import { EventTimeline } from './EventTimeline';
import { StateDetailPanel } from './StateDetailPanel';
import { TimelineScrubber } from './TimelineScrubber';
import { buildSnapshots } from './timeMachine';
import type { ExecutionDetail, HistoryEvent } from './types';

export function InspectorApp() {
  const selectedExecutionId = useInspectStore((s) => s.selectedExecutionId);
  const executionDetail = useInspectStore((s) => s.executionDetail);
  const setExecutionDetail = useInspectStore((s) => s.setExecutionDetail);
  const setEvents = useInspectStore((s) => s.setEvents);
  const appendEvents = useInspectStore((s) => s.appendEvents);
  const setSnapshots = useInspectStore((s) => s.setSnapshots);
  const setPlaybackIndex = useInspectStore((s) => s.setPlaybackIndex);
  const isLive = useInspectStore((s) => s.isLive);
  const nodes = useInspectStore((s) => s.nodes);
  const edges = useInspectStore((s) => s.edges);

  const handleExecutionInfo = useCallback(
    (detail: Omit<ExecutionDetail, 'history'>) => {
      setExecutionDetail(detail);
    },
    [setExecutionDetail],
  );

  const handleHistory = useCallback(
    (events: HistoryEvent[]) => {
      setEvents(events);
      const snaps = buildSnapshots(events, nodes, edges);
      setSnapshots(snaps);
      if (isLive) {
        setPlaybackIndex(snaps.length - 1);
      }
    },
    [setEvents, setSnapshots, setPlaybackIndex, isLive, nodes, edges],
  );

  const handleHistoryUpdate = useCallback(
    (events: HistoryEvent[]) => {
      appendEvents(events);
      // Rebuild snapshots with full event list
      const allEvents = useInspectStore.getState().events;
      const snaps = buildSnapshots(allEvents, nodes, edges);
      setSnapshots(snaps);
      if (isLive) {
        setPlaybackIndex(snaps.length - 1);
      }
    },
    [appendEvents, setSnapshots, setPlaybackIndex, isLive, nodes, edges],
  );

  useSSE({
    executionId: selectedExecutionId,
    onExecutionInfo: handleExecutionInfo,
    onHistory: handleHistory,
    onHistoryUpdate: handleHistoryUpdate,
  });

  return (
    <div className="app">
      <header className="app-header">
        <h1>RSF Execution Inspector</h1>
        <div className="header-right">
          <a href="#/editor" className="header-link">Editor</a>
        </div>
      </header>
      <div className="inspector-body">
        <div className="inspector-left">
          <ExecutionList />
        </div>
        <div className="inspector-center">
          {executionDetail && <ExecutionHeader />}
          <InspectorGraph />
          {executionDetail && <TimelineScrubber />}
        </div>
        <div className="inspector-right">
          <EventTimeline />
          <StateDetailPanel />
        </div>
      </div>
    </div>
  );
}
