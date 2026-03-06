import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function MapNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  const maxConcurrency = stateData.MaxConcurrency as number | undefined;
  const hasRetry = Array.isArray(stateData.Retry) && stateData.Retry.length > 0;
  const hasCatch = Array.isArray(stateData.Catch) && stateData.Catch.length > 0;

  const [ioExpanded, setIoExpanded] = useState(false);

  // Local state + refs for text fields (debounced, focus-guarded)
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const [localItemsPath, setLocalItemsPath] = useState<string>((stateData.ItemsPath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');
  const [localInputPath, setLocalInputPath] = useState<string>((stateData.InputPath as string) ?? '');
  const [localOutputPath, setLocalOutputPath] = useState<string>((stateData.OutputPath as string) ?? '');
  const [localResultPath, setLocalResultPath] = useState<string>((stateData.ResultPath as string) ?? '');

  const commentRef = useRef<HTMLInputElement>(null);
  const itemsPathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);
  const inputPathRef = useRef<HTMLInputElement>(null);
  const outputPathRef = useRef<HTMLInputElement>(null);
  const resultPathRef = useRef<HTMLInputElement>(null);

  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const itemsPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const outputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const resultPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state (YAML->graph direction) with focus guard
  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  useEffect(() => {
    if (document.activeElement === itemsPathRef.current) return;
    setLocalItemsPath(stateData.ItemsPath as string ?? '');
  }, [stateData.ItemsPath]);

  useEffect(() => {
    if (document.activeElement === queryLanguageRef.current) return;
    setLocalQueryLanguage(stateData.QueryLanguage as string ?? '');
  }, [stateData.QueryLanguage]);

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

  const handleCommentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalComment(val);
    clearTimeout(commentDebounceRef.current);
    commentDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Comment', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleItemsPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalItemsPath(val);
    clearTimeout(itemsPathDebounceRef.current);
    itemsPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'ItemsPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleMaxConcurrencyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const val = raw === '' ? undefined : Number(raw);
    updateStateProperty(id, 'MaxConcurrency', val);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
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

  const handleEndToggle = () => {
    const current = stateData.End === true;
    updateStateProperty(id, 'End', current ? undefined : true);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  // Read-only summaries
  const itemProcessorSummary = stateData.ItemProcessor != null
    ? 'ItemProcessor (edit in YAML)'
    : 'Not set';

  const itemSelectorSummary = stateData.ItemSelector != null
    ? `${Object.keys(stateData.ItemSelector as object).length} keys (edit in YAML)`
    : 'Not set';

  const retrySummary = Array.isArray(stateData.Retry) && stateData.Retry.length > 0
    ? `${stateData.Retry.length} polic${stateData.Retry.length !== 1 ? 'ies' : 'y'} (edit in YAML)`
    : 'Not set';

  const catchSummary = Array.isArray(stateData.Catch) && stateData.Catch.length > 0
    ? `${stateData.Catch.length} catcher${stateData.Catch.length !== 1 ? 's' : ''} (edit in YAML)`
    : 'Not set';

  const parametersSummary = stateData.Parameters != null
    ? `${Object.keys(stateData.Parameters as object).length} keys (edit in YAML)`
    : 'Not set';

  const resultSelectorSummary = stateData.ResultSelector != null
    ? `${Object.keys(stateData.ResultSelector as object).length} keys (edit in YAML)`
    : 'Not set';

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
        <label>ItemProcessor</label>
        <div className="readonly-summary">{itemProcessorSummary}</div>
      </div>
      <div className="property-field">
        <label>ItemsPath</label>
        <input
          ref={itemsPathRef}
          type="text"
          value={localItemsPath}
          onChange={handleItemsPathChange}
          placeholder="$.items"
        />
      </div>
      <div className="property-field">
        <label>MaxConcurrency</label>
        <input
          type="number"
          min="0"
          value={stateData.MaxConcurrency !== undefined ? String(stateData.MaxConcurrency) : ''}
          onChange={handleMaxConcurrencyChange}
          placeholder="None"
        />
      </div>
      <div className="property-field">
        <label>ItemSelector</label>
        <div className="readonly-summary">{itemSelectorSummary}</div>
      </div>
      <div className="property-field">
        <label>Retry</label>
        <div className="readonly-summary">{retrySummary}</div>
      </div>
      <div className="property-field">
        <label>Catch</label>
        <div className="readonly-summary">{catchSummary}</div>
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

      {/* I/O Processing collapsible section */}
      <div className="io-section">
        <div className="io-section-header" onClick={() => setIoExpanded((v) => !v)}>
          <span>I/O Processing</span>
          <span className={`io-section-chevron ${ioExpanded ? 'open' : ''}`}>&#8250;</span>
        </div>
        {ioExpanded && (
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
              <div className="readonly-summary">{parametersSummary}</div>
            </div>
            <div className="property-field">
              <label>ResultSelector</label>
              <div className="readonly-summary">{resultSelectorSummary}</div>
            </div>
            <div className="property-field">
              <label>Assign</label>
              <div className="readonly-summary">{assignSummary}</div>
            </div>
            <div className="property-field">
              <label>Output</label>
              <div className="readonly-summary">{outputSummary}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  ) : undefined;

  return (
    <BaseNode nodeProps={props} color="#1abc9c" icon="M" expandedContent={expandedContent}>
      <div className="node-badges">
        {maxConcurrency !== undefined && (
          <span className="badge badge-concurrency">max: {maxConcurrency}</span>
        )}
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
      </div>
    </BaseNode>
  );
}
