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
  // I/O Processing fields
  const [localInputPath, setLocalInputPath] = useState<string>((stateData.InputPath as string) ?? '');
  const [localOutputPath, setLocalOutputPath] = useState<string>((stateData.OutputPath as string) ?? '');
  const [localResultPath, setLocalResultPath] = useState<string>((stateData.ResultPath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');

  const [ioOpen, setIoOpen] = useState(false);

  const resultRef = useRef<HTMLTextAreaElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const inputPathRef = useRef<HTMLInputElement>(null);
  const outputPathRef = useRef<HTMLInputElement>(null);
  const resultPathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);

  const resultDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const outputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const resultPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

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

  useEffect(() => {
    if (document.activeElement === inputPathRef.current) return;
    setLocalInputPath(stateData.InputPath as string ?? '');
  }, [stateData.InputPath]);

  useEffect(() => {
    if (document.activeElement === outputPathRef.current) return;
    setLocalOutputPath(stateData.OutputPath as string ?? '');
  }, [stateData.OutputPath]);

  useEffect(() => {
    if (document.activeElement === resultPathRef.current) return;
    setLocalResultPath(stateData.ResultPath as string ?? '');
  }, [stateData.ResultPath]);

  useEffect(() => {
    if (document.activeElement === queryLanguageRef.current) return;
    setLocalQueryLanguage(stateData.QueryLanguage as string ?? '');
  }, [stateData.QueryLanguage]);

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

  const handleResultPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalResultPath(val);
    clearTimeout(resultPathDebounceRef.current);
    resultPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'ResultPath', val || undefined);
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

  const handleEndToggle = () => {
    const current = stateData.End === true;
    updateStateProperty(id, 'End', current ? undefined : true);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const expandedContent = isExpanded ? (
    <div className="property-editor">
      {/* 1. Result (textarea, JSON parse, debounce) */}
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

      {/* 2. Comment */}
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

      {/* 3. End toggle */}
      <div className="property-field property-field-toggle">
        <label>End</label>
        <button
          className={`toggle-btn ${stateData.End ? 'active' : ''}`}
          onClick={handleEndToggle}
        >
          {stateData.End ? 'Yes' : 'No'}
        </button>
      </div>

      {/* 4. Collapsible I/O Processing section */}
      <div className="io-section">
        <div className="io-section-header" onClick={() => setIoOpen(!ioOpen)}>
          <span className={`io-section-chevron ${ioOpen ? 'open' : ''}`}>&#9654;</span>
          I/O Processing
        </div>
        {ioOpen && (
          <div className="io-section-body">
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
              <label>ResultPath</label>
              <input
                ref={resultPathRef}
                type="text"
                value={localResultPath}
                onChange={handleResultPathChange}
                placeholder="$.result"
              />
            </div>
            <div className="property-field">
              <label>Parameters</label>
              <div className="readonly-summary">
                {stateData.Parameters
                  ? `{${Object.keys(stateData.Parameters as object).length} keys}`
                  : 'Not set'}
                <span className="edit-hint">(edit in YAML)</span>
              </div>
            </div>
            <div className="property-field">
              <label>ResultSelector</label>
              <div className="readonly-summary">
                {stateData.ResultSelector
                  ? `{${Object.keys(stateData.ResultSelector as object).length} keys}`
                  : 'Not set'}
                <span className="edit-hint">(edit in YAML)</span>
              </div>
            </div>
            <div className="property-field">
              <label>Assign</label>
              <div className="readonly-summary">
                {stateData.Assign
                  ? `{${Object.keys(stateData.Assign as object).length} keys}`
                  : 'Not set'}
                <span className="edit-hint">(edit in YAML)</span>
              </div>
            </div>
            <div className="property-field">
              <label>Output</label>
              <div className="readonly-summary">
                {stateData.Output
                  ? `{${Object.keys(stateData.Output as object).length} keys}`
                  : 'Not set'}
                <span className="edit-hint">(edit in YAML)</span>
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
        )}
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
