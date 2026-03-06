import { useState, useEffect, useRef } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { BaseNode } from './BaseNode';
import { useFlowStore } from '../store/flowStore';

export function FailNode(props: NodeProps<FlowNode>) {
  const { id, data } = props;
  const stateData = data.stateData || {};

  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const updateStateProperty = useFlowStore((s) => s.updateStateProperty);
  const isExpanded = expandedNodeId === id;

  // Determine initial active error type from stateData
  const initErrorType = (): 'static' | 'path' | null => {
    if (stateData.Error != null) return 'static';
    if (stateData.ErrorPath != null) return 'path';
    return null;
  };

  const initCauseType = (): 'static' | 'path' | null => {
    if (stateData.Cause != null) return 'static';
    if (stateData.CausePath != null) return 'path';
    return null;
  };

  const [activeErrorType, setActiveErrorType] = useState<'static' | 'path' | null>(initErrorType);
  const [activeCauseType, setActiveCauseType] = useState<'static' | 'path' | null>(initCauseType);

  // Local state + refs for text fields (debounced, focus-guarded)
  const [localComment, setLocalComment] = useState<string>((stateData.Comment as string) ?? '');
  const [localError, setLocalError] = useState<string>((stateData.Error as string) ?? '');
  const [localErrorPath, setLocalErrorPath] = useState<string>((stateData.ErrorPath as string) ?? '');
  const [localCause, setLocalCause] = useState<string>((stateData.Cause as string) ?? '');
  const [localCausePath, setLocalCausePath] = useState<string>((stateData.CausePath as string) ?? '');
  const [localQueryLanguage, setLocalQueryLanguage] = useState<string>((stateData.QueryLanguage as string) ?? '');

  const commentRef = useRef<HTMLInputElement>(null);
  const errorRef = useRef<HTMLInputElement>(null);
  const errorPathRef = useRef<HTMLInputElement>(null);
  const causeRef = useRef<HTMLInputElement>(null);
  const causePathRef = useRef<HTMLInputElement>(null);
  const queryLanguageRef = useRef<HTMLInputElement>(null);

  const commentDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const errorDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const errorPathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const causeDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const causePathDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const queryLanguageDebounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync from store to local state with focus guard
  useEffect(() => {
    if (document.activeElement === commentRef.current) return;
    setLocalComment(stateData.Comment as string ?? '');
  }, [stateData.Comment]);

  useEffect(() => {
    if (document.activeElement === errorRef.current) return;
    setLocalError(stateData.Error as string ?? '');
  }, [stateData.Error]);

  useEffect(() => {
    if (document.activeElement === errorPathRef.current) return;
    setLocalErrorPath(stateData.ErrorPath as string ?? '');
  }, [stateData.ErrorPath]);

  useEffect(() => {
    if (document.activeElement === causeRef.current) return;
    setLocalCause(stateData.Cause as string ?? '');
  }, [stateData.Cause]);

  useEffect(() => {
    if (document.activeElement === causePathRef.current) return;
    setLocalCausePath(stateData.CausePath as string ?? '');
  }, [stateData.CausePath]);

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

  // Error radio pair handlers
  const handleErrorTypeSelect = (type: 'static' | 'path') => {
    setActiveErrorType(type);
    if (type === 'static') {
      // Clear ErrorPath when switching to static
      updateStateProperty(id, 'ErrorPath', undefined);
      setLocalErrorPath('');
    } else {
      // Clear Error when switching to path
      updateStateProperty(id, 'Error', undefined);
      setLocalError('');
    }
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleErrorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalError(val);
    clearTimeout(errorDebounceRef.current);
    errorDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Error', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleErrorPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalErrorPath(val);
    clearTimeout(errorPathDebounceRef.current);
    errorPathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'ErrorPath', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  // Cause radio pair handlers
  const handleCauseTypeSelect = (type: 'static' | 'path') => {
    setActiveCauseType(type);
    if (type === 'static') {
      // Clear CausePath when switching to static
      updateStateProperty(id, 'CausePath', undefined);
      setLocalCausePath('');
    } else {
      // Clear Cause when switching to path
      updateStateProperty(id, 'Cause', undefined);
      setLocalCause('');
    }
    document.dispatchEvent(new CustomEvent('rsf-graph-change'));
  };

  const handleCauseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalCause(val);
    clearTimeout(causeDebounceRef.current);
    causeDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'Cause', val || undefined);
      document.dispatchEvent(new CustomEvent('rsf-graph-change'));
    }, 300);
  };

  const handleCausePathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setLocalCausePath(val);
    clearTimeout(causePathDebounceRef.current);
    causePathDebounceRef.current = setTimeout(() => {
      updateStateProperty(id, 'CausePath', val || undefined);
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

      {/* Error / ErrorPath radio pair */}
      <div className="property-field">
        <label>Error</label>
        <div className="radio-group">
          <div className={`radio-option ${activeErrorType !== 'static' ? 'disabled' : ''}`}>
            <input
              type="radio"
              name={`error-type-${id}`}
              checked={activeErrorType === 'static'}
              onChange={() => handleErrorTypeSelect('static')}
            />
            <span>Error</span>
            <input
              ref={errorRef}
              type="text"
              value={localError}
              onChange={handleErrorChange}
              disabled={activeErrorType !== 'static'}
              placeholder="States.ALL"
            />
          </div>
          <div className={`radio-option ${activeErrorType !== 'path' ? 'disabled' : ''}`}>
            <input
              type="radio"
              name={`error-type-${id}`}
              checked={activeErrorType === 'path'}
              onChange={() => handleErrorTypeSelect('path')}
            />
            <span>ErrorPath</span>
            <input
              ref={errorPathRef}
              type="text"
              value={localErrorPath}
              onChange={handleErrorPathChange}
              disabled={activeErrorType !== 'path'}
              placeholder="$.errorCode"
            />
          </div>
        </div>
      </div>

      {/* Cause / CausePath radio pair */}
      <div className="property-field">
        <label>Cause</label>
        <div className="radio-group">
          <div className={`radio-option ${activeCauseType !== 'static' ? 'disabled' : ''}`}>
            <input
              type="radio"
              name={`cause-type-${id}`}
              checked={activeCauseType === 'static'}
              onChange={() => handleCauseTypeSelect('static')}
            />
            <span>Cause</span>
            <input
              ref={causeRef}
              type="text"
              value={localCause}
              onChange={handleCauseChange}
              disabled={activeCauseType !== 'static'}
              placeholder="Error description"
            />
          </div>
          <div className={`radio-option ${activeCauseType !== 'path' ? 'disabled' : ''}`}>
            <input
              type="radio"
              name={`cause-type-${id}`}
              checked={activeCauseType === 'path'}
              onChange={() => handleCauseTypeSelect('path')}
            />
            <span>CausePath</span>
            <input
              ref={causePathRef}
              type="text"
              value={localCausePath}
              onChange={handleCausePathChange}
              disabled={activeCauseType !== 'path'}
              placeholder="$.causeMessage"
            />
          </div>
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
    <BaseNode nodeProps={props} color="#e74c3c" icon="&#10007;" expandedContent={expandedContent}>
      {(stateData.Error != null || stateData.Cause != null) && (
        <div className="node-detail">
          {stateData.Error != null && (
            <div className="detail-line">Error: {String(stateData.Error)}</div>
          )}
          {stateData.Cause != null && (
            <div className="detail-line">Cause: {String(stateData.Cause)}</div>
          )}
        </div>
      )}
    </BaseNode>
  );
}
