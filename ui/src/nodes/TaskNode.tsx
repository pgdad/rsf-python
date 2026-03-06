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

  // Determine active timeout type from stateData
  const getActiveTimeoutType = (): 'static' | 'path' | null => {
    if (stateData.TimeoutSeconds !== undefined) return 'static';
    if (stateData.TimeoutSecondsPath) return 'path';
    return null;
  };

  // Determine active heartbeat type from stateData
  const getActiveHeartbeatType = (): 'static' | 'path' | null => {
    if (stateData.HeartbeatSeconds !== undefined) return 'static';
    if (stateData.HeartbeatSecondsPath) return 'path';
    return null;
  };

  const [activeTimeoutType, setActiveTimeoutType] = useState<'static' | 'path' | null>(getActiveTimeoutType);
  const [activeHeartbeatType, setActiveHeartbeatType] = useState<'static' | 'path' | null>(getActiveHeartbeatType);
  const [ioOpen, setIoOpen] = useState(false);

  // Local state + refs for text fields (debounced, focus-guarded)
  const [localResource, setLocalResource] = useState<string>((stateData.Resource as string) ?? '');
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const [localTimeoutSecondsPath, setLocalTimeoutSecondsPath] = useState<string>((stateData.TimeoutSecondsPath as string) ?? '');
  const [localHeartbeatSecondsPath, setLocalHeartbeatSecondsPath] = useState<string>((stateData.HeartbeatSecondsPath as string) ?? '');
  const [localSubWorkflow, setLocalSubWorkflow] = useState<string>((stateData.SubWorkflow as string) ?? '');
  // I/O Processing fields
  const [localInputPath, setLocalInputPath] = useState<string>((stateData.InputPath as string) ?? '');
  const [localOutputPath, setLocalOutputPath] = useState<string>((stateData.OutputPath as string) ?? '');
  const [localResultPath, setLocalResultPath] = useState<string>((stateData.ResultPath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');

  const resourceRef = useRef<HTMLInputElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const timeoutSecondsPathRef = useRef<HTMLInputElement>(null);
  const heartbeatSecondsPathRef = useRef<HTMLInputElement>(null);
  const subWorkflowRef = useRef<HTMLInputElement>(null);
  const inputPathRef = useRef<HTMLInputElement>(null);
  const outputPathRef = useRef<HTMLInputElement>(null);
  const resultPathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);

  const resourceDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const timeoutSecondsPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const heartbeatSecondsPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const subWorkflowDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const outputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const resultPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync active radio types when stateData changes from external source (YAML edit)
  useEffect(() => {
    setActiveTimeoutType(getActiveTimeoutType());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stateData.TimeoutSeconds, stateData.TimeoutSecondsPath]);

  useEffect(() => {
    setActiveHeartbeatType(getActiveHeartbeatType());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stateData.HeartbeatSeconds, stateData.HeartbeatSecondsPath]);

  // Sync from store to local state (YAML->graph direction) with focus guard
  useEffect(() => {
    if (document.activeElement === resourceRef.current) return;
    setLocalResource(stateData.Resource as string ?? '');
  }, [stateData.Resource]);

  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  useEffect(() => {
    if (document.activeElement === timeoutSecondsPathRef.current) return;
    setLocalTimeoutSecondsPath(stateData.TimeoutSecondsPath as string ?? '');
  }, [stateData.TimeoutSecondsPath]);

  useEffect(() => {
    if (document.activeElement === heartbeatSecondsPathRef.current) return;
    setLocalHeartbeatSecondsPath(stateData.HeartbeatSecondsPath as string ?? '');
  }, [stateData.HeartbeatSecondsPath]);

  useEffect(() => {
    if (document.activeElement === subWorkflowRef.current) return;
    setLocalSubWorkflow(stateData.SubWorkflow as string ?? '');
  }, [stateData.SubWorkflow]);

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

  // Timeout radio pair handlers
  const handleTimeoutRadioChange = (type: 'static' | 'path') => {
    if (type === 'static') {
      updateStateProperty(id, 'TimeoutSecondsPath', undefined);
    } else {
      updateStateProperty(id, 'TimeoutSeconds', undefined);
    }
    setActiveTimeoutType(type);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  // Heartbeat radio pair handlers
  const handleHeartbeatRadioChange = (type: 'static' | 'path') => {
    if (type === 'static') {
      updateStateProperty(id, 'HeartbeatSecondsPath', undefined);
    } else {
      updateStateProperty(id, 'HeartbeatSeconds', undefined);
    }
    setActiveHeartbeatType(type);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

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

  const handleTimeoutSecondsPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalTimeoutSecondsPath(val);
    clearTimeout(timeoutSecondsPathDebounceRef.current);
    timeoutSecondsPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'TimeoutSecondsPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleHeartbeatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const val = raw === '' ? undefined : Number(raw);
    updateStateProperty(id, 'HeartbeatSeconds', val);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleHeartbeatSecondsPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalHeartbeatSecondsPath(val);
    clearTimeout(heartbeatSecondsPathDebounceRef.current);
    heartbeatSecondsPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'HeartbeatSecondsPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleSubWorkflowChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalSubWorkflow(val);
    clearTimeout(subWorkflowDebounceRef.current);
    subWorkflowDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'SubWorkflow', val || undefined);
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
      {/* 1. Resource */}
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

      {/* 3. Timeout radio pair: TimeoutSeconds / TimeoutSecondsPath (optional) */}
      <div className="radio-group">
        <div className={`radio-option ${activeTimeoutType !== 'static' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`timeout-${id}`}
            value="static"
            checked={activeTimeoutType === 'static'}
            onChange={() => handleTimeoutRadioChange('static')}
          />
          <div className="radio-input">
            <label>TimeoutSeconds</label>
            <input
              type="number"
              min="0"
              disabled={activeTimeoutType !== 'static'}
              value={stateData.TimeoutSeconds !== undefined ? String(stateData.TimeoutSeconds) : ''}
              onChange={handleTimeoutChange}
              placeholder="None"
            />
          </div>
        </div>
        <div className={`radio-option ${activeTimeoutType !== 'path' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`timeout-${id}`}
            value="path"
            checked={activeTimeoutType === 'path'}
            onChange={() => handleTimeoutRadioChange('path')}
          />
          <div className="radio-input">
            <label>TimeoutSecondsPath</label>
            <input
              ref={timeoutSecondsPathRef}
              type="text"
              disabled={activeTimeoutType !== 'path'}
              value={localTimeoutSecondsPath}
              onChange={handleTimeoutSecondsPathChange}
              placeholder="$.timeout"
            />
          </div>
        </div>
      </div>

      {/* 4. Heartbeat radio pair: HeartbeatSeconds / HeartbeatSecondsPath (optional) */}
      <div className="radio-group">
        <div className={`radio-option ${activeHeartbeatType !== 'static' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`heartbeat-${id}`}
            value="static"
            checked={activeHeartbeatType === 'static'}
            onChange={() => handleHeartbeatRadioChange('static')}
          />
          <div className="radio-input">
            <label>HeartbeatSeconds</label>
            <input
              type="number"
              min="0"
              disabled={activeHeartbeatType !== 'static'}
              value={stateData.HeartbeatSeconds !== undefined ? String(stateData.HeartbeatSeconds) : ''}
              onChange={handleHeartbeatChange}
              placeholder="None"
            />
          </div>
        </div>
        <div className={`radio-option ${activeHeartbeatType !== 'path' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`heartbeat-${id}`}
            value="path"
            checked={activeHeartbeatType === 'path'}
            onChange={() => handleHeartbeatRadioChange('path')}
          />
          <div className="radio-input">
            <label>HeartbeatSecondsPath</label>
            <input
              ref={heartbeatSecondsPathRef}
              type="text"
              disabled={activeHeartbeatType !== 'path'}
              value={localHeartbeatSecondsPath}
              onChange={handleHeartbeatSecondsPathChange}
              placeholder="$.heartbeat"
            />
          </div>
        </div>
      </div>

      {/* 5. Retry (read-only summary) */}
      <div className="property-field">
        <label>Retry</label>
        <div className="readonly-summary">
          {Array.isArray(stateData.Retry) && stateData.Retry.length > 0
            ? `${stateData.Retry.length} polic${stateData.Retry.length === 1 ? 'y' : 'ies'}`
            : 'Not set'}
          <span className="edit-hint">(edit in YAML)</span>
        </div>
      </div>

      {/* 6. Catch (read-only summary) */}
      <div className="property-field">
        <label>Catch</label>
        <div className="readonly-summary">
          {Array.isArray(stateData.Catch) && stateData.Catch.length > 0
            ? `${stateData.Catch.length} catcher${stateData.Catch.length === 1 ? '' : 's'}`
            : 'Not set'}
          <span className="edit-hint">(edit in YAML)</span>
        </div>
      </div>

      {/* 7. SubWorkflow */}
      <div className="property-field">
        <label>SubWorkflow</label>
        <input
          ref={subWorkflowRef}
          type="text"
          value={localSubWorkflow}
          onChange={handleSubWorkflowChange}
          placeholder="Optional sub-workflow"
        />
      </div>

      {/* 8. End toggle */}
      <div className="property-field property-field-toggle">
        <label>End</label>
        <button
          className={`toggle-btn ${stateData.End ? 'active' : ''}`}
          onClick={handleEndToggle}
        >
          {stateData.End ? 'Yes' : 'No'}
        </button>
      </div>

      {/* 9. Collapsible I/O Processing section */}
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
    <BaseNode nodeProps={props} color="#4a90d9" icon="T" expandedContent={expandedContent}>
      <div className="node-badges">
        {hasRetry && <span className="badge badge-retry">Retry</span>}
        {hasCatch && <span className="badge badge-catch">Catch</span>}
        {timeout && <span className="badge badge-timeout">{timeout}s</span>}
      </div>
    </BaseNode>
  );
}
