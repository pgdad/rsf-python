import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function TaskNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  const hasRetry = Array.isArray(stateData.Retry) && stateData.Retry.length > 0;
  const hasCatch = Array.isArray(stateData.Catch) && stateData.Catch.length > 0;
  const timeout = stateData.TimeoutSeconds as number | undefined;

  // Local state + refs for text fields (debounced, focus-guarded)
  const [localResource, setLocalResource] = useState<string>((stateData.Resource as string) ?? '');
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const resourceRef = useRef<HTMLInputElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const resourceDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state (YAML->graph direction) with focus guard
  useEffect(() => {
    if (document.activeElement === resourceRef.current) return;
    setLocalResource(stateData.Resource as string ?? '');
  }, [stateData.Resource]);

  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  const handleResourceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalResource(val);
    clearTimeout(resourceDebounceRef.current);
    resourceDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Resource', val || undefined);
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

  const handleTimeoutChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const val = raw === '' ? undefined : Number(raw);
    updateStateProperty(id, 'TimeoutSeconds', val);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleHeartbeatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const val = raw === '' ? undefined : Number(raw);
    updateStateProperty(id, 'HeartbeatSeconds', val);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleEndToggle = () => {
    const current = stateData.End === true;
    updateStateProperty(id, 'End', current ? undefined : true);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const expandedContent = isExpanded ? (
    <div className="property-editor">
      <div className="property-field">
        <label>Resource</label>
        <input
          ref={resourceRef}
          type="text"
          value={localResource}
          onChange={handleResourceChange}
          placeholder="arn:..."
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
      <div className="property-field">
        <label>TimeoutSeconds</label>
        <input
          type="number"
          min="0"
          value={stateData.TimeoutSeconds !== undefined ? String(stateData.TimeoutSeconds) : ''}
          onChange={handleTimeoutChange}
          placeholder="None"
        />
      </div>
      <div className="property-field">
        <label>HeartbeatSeconds</label>
        <input
          type="number"
          min="0"
          value={stateData.HeartbeatSeconds !== undefined ? String(stateData.HeartbeatSeconds) : ''}
          onChange={handleHeartbeatChange}
          placeholder="None"
        />
      </div>
      <div className="property-field property-field-toggle">
        <label>End</label>
        <button
          className={`toggle-btn ${stateData.End ? 'active' : ''}`}
          onClick={handleEndToggle}
        >
          {stateData.End ? 'Yes' : 'No'}
        </button>
      </div>
    </div>
  ) : undefined;

  return (
    <BaseNode nodeProps={props} color="#4a90d9" icon="T" expandedContent={expandedContent}>
      <div className="node-badges">
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
        {timeout && <span className="badge badge-timeout">{timeout}s</span>}
      </div>
    </BaseNode>
  );
}
