import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function PassNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  const hasResult = stateData.Result !== undefined;

  // Local state for text/textarea fields
  const resultValue = stateData.Result !== undefined
    ? (typeof stateData.Result === 'object'
      ? JSON.stringify(stateData.Result, null, 2)
      : String(stateData.Result))
    : '';

  const [localResult, setLocalResult] = useState<string>(resultValue);
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const resultRef = useRef<HTMLTextAreaElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const resultDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state (YAML->graph direction) with focus guard
  useEffect(() => {
    if (document.activeElement === resultRef.current) return;
    const newVal = stateData.Result !== undefined
      ? (typeof stateData.Result === 'object'
        ? JSON.stringify(stateData.Result, null, 2)
        : String(stateData.Result))
      : '';
    setLocalResult(newVal);
  }, [stateData.Result]);

  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  const handleResultChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setLocalResult(val);
    clearTimeout(resultDebounceRef.current);
    resultDebounceRef.current = setTimeout(() => {
      if (val === '' || val === undefined) {
        updateStateProperty(id, 'Result', undefined);
      } else {
        try {
          const parsed = JSON.parse(val);
          updateStateProperty(id, 'Result', parsed);
        } catch {
          updateStateProperty(id, 'Result', val);
        }
      }
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

  const handleEndToggle = () => {
    const current = stateData.End === true;
    updateStateProperty(id, 'End', current ? undefined : true);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const expandedContent = isExpanded ? (
    <div className="property-editor">
      <div className="property-field">
        <label>Result (JSON)</label>
        <textarea
          ref={resultRef}
          value={localResult}
          onChange={handleResultChange}
          placeholder="{}"
          rows={3}
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
    <BaseNode nodeProps={props} color="#7b68ee" icon="P" expandedContent={expandedContent}>
      {hasResult && (
        <div className="node-badges">
          <span className="badge badge-result">Result</span>
        </div>
      )}
    </BaseNode>
  );
}
