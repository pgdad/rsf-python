import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function WaitNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  const seconds = stateData.Seconds as number | undefined;
  const timestamp = stateData.Timestamp as string | undefined;

  let waitDisplay = '';
  if (seconds !== undefined) waitDisplay = `${seconds}s`;
  else if (timestamp) waitDisplay = timestamp;
  else if (stateData.SecondsPath) waitDisplay = 'Path';
  else if (stateData.TimestampPath) waitDisplay = 'Path';

  // Local state for text fields (debounced, focus-guarded)
  const [localTimestamp, setLocalTimestamp] = useState<string>((stateData.Timestamp as string) ?? '');
  const [localSecondsPath, setLocalSecondsPath] = useState<string>((stateData.SecondsPath as string) ?? '');
  const [localTimestampPath, setLocalTimestampPath] = useState<string>((stateData.TimestampPath as string) ?? '');
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const timestampRef = useRef<HTMLInputElement>(null);
  const secondsPathRef = useRef<HTMLInputElement>(null);
  const timestampPathRef = useRef<HTMLInputElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const timestampDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const secondsPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const timestampPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state with focus guard
  useEffect(() => {
    if (document.activeElement === timestampRef.current) return;
    setLocalTimestamp(stateData.Timestamp as string ?? '');
  }, [stateData.Timestamp]);

  useEffect(() => {
    if (document.activeElement === secondsPathRef.current) return;
    setLocalSecondsPath(stateData.SecondsPath as string ?? '');
  }, [stateData.SecondsPath]);

  useEffect(() => {
    if (document.activeElement === timestampPathRef.current) return;
    setLocalTimestampPath(stateData.TimestampPath as string ?? '');
  }, [stateData.TimestampPath]);

  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  const handleSecondsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const val = raw === '' ? undefined : Number(raw);
    updateStateProperty(id, 'Seconds', val);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleTimestampChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalTimestamp(val);
    clearTimeout(timestampDebounceRef.current);
    timestampDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Timestamp', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleSecondsPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSecondsPath(val);
    clearTimeout(secondsPathDebounceRef.current);
    secondsPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'SecondsPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleTimestampPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalTimestampPath(val);
    clearTimeout(timestampPathDebounceRef.current);
    timestampPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'TimestampPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleCommentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalComment(val);
    clearTimeout(commentDebounceRef.current);
    commentDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Comment', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const expandedContent = isExpanded ? (
    <div className="property-editor">
      <div className="property-field">
        <label>Seconds</label>
        <input
          type="number"
          min="0"
          value={stateData.Seconds !== undefined ? String(stateData.Seconds) : ''}
          onChange={handleSecondsChange}
          placeholder="None"
        />
      </div>
      <div className="property-field">
        <label>Timestamp</label>
        <input
          ref={timestampRef}
          type="text"
          value={localTimestamp}
          onChange={handleTimestampChange}
          placeholder="2024-01-01T00:00:00Z"
        />
      </div>
      <div className="property-field">
        <label>SecondsPath</label>
        <input
          ref={secondsPathRef}
          type="text"
          value={localSecondsPath}
          onChange={handleSecondsPathChange}
          placeholder="$.delay"
        />
      </div>
      <div className="property-field">
        <label>TimestampPath</label>
        <input
          ref={timestampPathRef}
          type="text"
          value={localTimestampPath}
          onChange={handleTimestampPathChange}
          placeholder="$.timestamp"
        />
      </div>
      <div className="property-field">
        <label>Comment</label>
        <input
          ref={commentRef}
          type="text"
          value={localComment}
          onChange={handleCommentChange}
          placeholder="Optional comment"
        />
      </div>
    </div>
  ) : undefined;

  return (
    <BaseNode nodeProps={props} color="#9b59b6" icon="W" expandedContent={expandedContent}>
      {waitDisplay && (
        <div className="node-badges">
          <span className="badge badge-wait">{waitDisplay}</span>
        </div>
      )}
    </BaseNode>
  );
}
