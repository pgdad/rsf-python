/**
 * Validation overlay showing errors as a list and badges on nodes.
 */

import { useFlowStore } from '../store/flowStore';

export function ValidationOverlay() {
  const errors = useFlowStore((s) => s.validationErrors);

  if (errors.length === 0) return null;

  const errorCount = errors.filter((e) => e.severity === 'error').length;
  const warningCount = errors.filter((e) => e.severity === 'warning').length;

  return (
    <div className="validation-overlay">
      <div className="validation-header">
        {errorCount > 0 && (
          <span className="validation-count error-count">
            {errorCount} error{errorCount !== 1 ? 's' : ''}
          </span>
        )}
        {warningCount > 0 && (
          <span className="validation-count warning-count">
            {warningCount} warning{warningCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      <div className="validation-list">
        {errors.map((error, idx) => (
          <div
            key={idx}
            className={`validation-item ${error.severity}`}
          >
            <span className="validation-icon">
              {error.severity === 'error' ? '\u2716' : '\u26A0'}
            </span>
            <span className="validation-message">{error.message}</span>
            {error.path && (
              <span className="validation-path">{error.path}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
