import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function ChoiceNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  const choices = Array.isArray(stateData.Choices) ? stateData.Choices.length : 0;
  const hasDefault = stateData.Default !== undefined;

  // Local state + refs for text fields (debounced, focus-guarded)
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const [localDefault, setLocalDefault] = useState<string>((stateData.Default as string) ?? '');
  const [localInputPath, setLocalInputPath] = useState<string>((stateData.InputPath as string) ?? '');
  const [localOutputPath, setLocalOutputPath] = useState<string>((stateData.OutputPath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');

  const commentRef = useRef<HTMLInputElement>(null);
  const defaultRef = useRef<HTMLInputElement>(null);
  const inputPathRef = useRef<HTMLInputElement>(null);
  const outputPathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);

  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const defaultDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const outputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state (YAML->graph direction) with focus guard
  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  useEffect(() => {
    if (document.activeElement === defaultRef.current) return;
    setLocalDefault(stateData.Default as string ?? '');
  }, [stateData.Default]);

  useEffect(() => {
    if (document.activeElement === inputPathRef.current) return;
    setLocalInputPath(stateData.InputPath as string ?? '');
  }, [stateData.InputPath]);

  useEffect(() => {
    if (document.activeElement === outputPathRef.current) return;
    setLocalOutputPath(stateData.OutputPath as string ?? '');
  }, [stateData.OutputPath]);

  useEffect(() => {
    if (document.activeElement === queryLanguageRef.current) return;
    setLocalQueryLanguage(stateData.QueryLanguage as string ?? '');
  }, [stateData.QueryLanguage]);

  const handleCommentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalComment(val);
    clearTimeout(commentDebounceRef.current);
    commentDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Comment', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleDefaultChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalDefault(val);
    clearTimeout(defaultDebounceRef.current);
    defaultDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Default', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleInputPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalInputPath(val);
    clearTimeout(inputPathDebounceRef.current);
    inputPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'InputPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleOutputPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalOutputPath(val);
    clearTimeout(outputPathDebounceRef.current);
    outputPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'OutputPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleQueryLanguageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalQueryLanguage(val);
    clearTimeout(queryLanguageDebounceRef.current);
    queryLanguageDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'QueryLanguage', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  // Read-only summaries for complex fields
  const choicesSummary = `${choices} rule${choices !== 1 ? 's' : ''} (edit in YAML)`;

  const assignSummary = stateData.Assign != null
    ? `${Object.keys(stateData.Assign as object).length} keys (edit in YAML)`
    : 'Not set';

  const outputSummary = stateData.Output != null
    ? (typeof stateData.Output === 'object'
      ? `${Object.keys(stateData.Output as object).length} keys (edit in YAML)`
      : `${String(stateData.Output)} (edit in YAML)`)
    : 'Not set';

  const expandedContent = isExpanded ? (
    <div className="property-editor">
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
        <label>Choices</label>
        <div className="readonly-summary">{choicesSummary}</div>
      </div>
      <div className="property-field">
        <label>Default</label>
        <input
          ref={defaultRef}
          type="text"
          value={localDefault}
          onChange={handleDefaultChange}
          placeholder="FallbackState"
        />
      </div>
      <div className="property-field">
        <label>InputPath</label>
        <input
          ref={inputPathRef}
          type="text"
          value={localInputPath}
          onChange={handleInputPathChange}
          placeholder="$.input"
        />
      </div>
      <div className="property-field">
        <label>OutputPath</label>
        <input
          ref={outputPathRef}
          type="text"
          value={localOutputPath}
          onChange={handleOutputPathChange}
          placeholder="$.output"
        />
      </div>
      <div className="property-field">
        <label>Assign</label>
        <div className="readonly-summary">
          {assignSummary}
          {stateData.Assign != null && <span className="edit-hint">edit in YAML</span>}
        </div>
      </div>
      <div className="property-field">
        <label>Output</label>
        <div className="readonly-summary">
          {outputSummary}
          {stateData.Output != null && <span className="edit-hint">edit in YAML</span>}
        </div>
      </div>
      <div className="property-field">
        <label>QueryLanguage</label>
        <input
          ref={queryLanguageRef}
          type="text"
          value={localQueryLanguage}
          onChange={handleQueryLanguageChange}
          placeholder="JSONPath"
        />
      </div>
    </div>
  ) : undefined;

  return (
    <BaseNode nodeProps={props} color="#e6a817" icon="?" expandedContent={expandedContent}>
      <div className="node-badges">
        <span className="badge badge-rules">{choices} rules</span>
        {hasDefault && <span className="badge badge-default">Default</span>}
      </div>
    </BaseNode>
  );
}
