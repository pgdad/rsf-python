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

  // Determine active radio from stateData
  const getActiveWaitType = (): string | null => {
    if (stateData.Seconds !== undefined) return 'Seconds';
    if (stateData.Timestamp) return 'Timestamp';
    if (stateData.SecondsPath) return 'SecondsPath';
    if (stateData.TimestampPath) return 'TimestampPath';
    return null;
  };

  const [activeWaitType, setActiveWaitType] = useState<string | null>(getActiveWaitType);
  const [ioOpen, setIoOpen] = useState(false);

  // Local state for text fields (debounced, focus-guarded)
  const [localTimestamp, setLocalTimestamp] = useState<string>((stateData.Timestamp as string) ?? '');
  const [localSecondsPath, setLocalSecondsPath] = useState<string>((stateData.SecondsPath as string) ?? '');
  const [localTimestampPath, setLocalTimestampPath] = useState<string>((stateData.TimestampPath as string) ?? '');
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  // I/O Processing fields
  const [localInputPath, setLocalInputPath] = useState<string>((stateData.InputPath as string) ?? '');
  const [localOutputPath, setLocalOutputPath] = useState<string>((stateData.OutputPath as string) ?? '');
  const [localResultPath, setLocalResultPath] = useState<string>((stateData.ResultPath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');

  const timestampRef = useRef<HTMLInputElement>(null);
  const secondsPathRef = useRef<HTMLInputElement>(null);
  const timestampPathRef = useRef<HTMLInputElement>(null);
  const commentRef = useRef<HTMLInputElement>(null);
  const inputPathRef = useRef<HTMLInputElement>(null);
  const outputPathRef = useRef<HTMLInputElement>(null);
  const resultPathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);

  const timestampDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const secondsPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const timestampPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const outputPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const resultPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync active radio when stateData changes from external source (YAML edit)
  useEffect(() => {
    setActiveWaitType(getActiveWaitType());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stateData.Seconds, stateData.Timestamp, stateData.SecondsPath, stateData.TimestampPath]);

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

  const handleRadioChange = (type: string) => {
    const allFields = ['Seconds', 'Timestamp', 'SecondsPath', 'TimestampPath'];
    for (const field of allFields) {
      if (field !== type) {
        updateStateProperty(id, field, undefined);
      }
    }
    setActiveWaitType(type);
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

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

  const expandedContent = isExpanded ? (
    <div className="property-editor">
      {/* 4-option radio group for duration — exactly one is required */}
      <div className="radio-group">
        <div className={`radio-option ${activeWaitType !== 'Seconds' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`wait-${id}`}
            value="Seconds"
            checked={activeWaitType === 'Seconds'}
            onChange={() => handleRadioChange('Seconds')}
          />
          <div className="radio-input">
            <label>
              Seconds {activeWaitType === 'Seconds' && <span className="required-asterisk">*</span>}
            </label>
            <input
              type="number"
              min="0"
              disabled={activeWaitType !== 'Seconds'}
              value={stateData.Seconds !== undefined ? String(stateData.Seconds) : ''}
              onChange={handleSecondsChange}
              placeholder="e.g. 60"
            />
          </div>
        </div>
        <div className={`radio-option ${activeWaitType !== 'Timestamp' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`wait-${id}`}
            value="Timestamp"
            checked={activeWaitType === 'Timestamp'}
            onChange={() => handleRadioChange('Timestamp')}
          />
          <div className="radio-input">
            <label>
              Timestamp {activeWaitType === 'Timestamp' && <span className="required-asterisk">*</span>}
            </label>
            <input
              ref={timestampRef}
              type="text"
              disabled={activeWaitType !== 'Timestamp'}
              value={localTimestamp}
              onChange={handleTimestampChange}
              placeholder="2024-01-01T00:00:00Z"
            />
          </div>
        </div>
        <div className={`radio-option ${activeWaitType !== 'SecondsPath' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`wait-${id}`}
            value="SecondsPath"
            checked={activeWaitType === 'SecondsPath'}
            onChange={() => handleRadioChange('SecondsPath')}
          />
          <div className="radio-input">
            <label>
              SecondsPath {activeWaitType === 'SecondsPath' && <span className="required-asterisk">*</span>}
            </label>
            <input
              ref={secondsPathRef}
              type="text"
              disabled={activeWaitType !== 'SecondsPath'}
              value={localSecondsPath}
              onChange={handleSecondsPathChange}
              placeholder="$.delay"
            />
          </div>
        </div>
        <div className={`radio-option ${activeWaitType !== 'TimestampPath' ? 'disabled' : ''}`}>
          <input
            type="radio"
            name={`wait-${id}`}
            value="TimestampPath"
            checked={activeWaitType === 'TimestampPath'}
            onChange={() => handleRadioChange('TimestampPath')}
          />
          <div className="radio-input">
            <label>
              TimestampPath {activeWaitType === 'TimestampPath' && <span className="required-asterisk">*</span>}
            </label>
            <input
              ref={timestampPathRef}
              type="text"
              disabled={activeWaitType !== 'TimestampPath'}
              value={localTimestampPath}
              onChange={handleTimestampPathChange}
              placeholder="$.timestamp"
            />
          </div>
        </div>
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

      {/* Collapsible I/O Processing section */}
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
    <BaseNode nodeProps={props} color="#9b59b6" icon="W" expandedContent={expandedContent}>
      {waitDisplay && (
        <div className="node-badges">
          <span className="badge badge-wait">{waitDisplay}</span>
        </div>
      )}
    </BaseNode>
  );
}
