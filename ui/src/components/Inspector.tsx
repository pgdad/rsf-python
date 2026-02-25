/**
 * Inspector panel for editing selected node properties.
 */

import { useFlowStore } from '../store/flowStore';

export function Inspector() {
  const selectedNodeId = useFlowStore((s) => s.selectedNodeId);
  const nodes = useFlowStore((s) => s.nodes);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  if (!selectedNode) {
    return (
      <div className="inspector">
        <div className="pane-header">Properties</div>
        <div className="inspector-empty">Select a node to view properties</div>
      </div>
    );
  }

  const stateData = selectedNode.data.stateData || {};

  return (
    <div className="inspector">
      <div className="pane-header">Properties</div>
      <div className="inspector-content">
        <div className="inspector-field">
          <label>Name</label>
          <input type="text" value={selectedNode.data.label} readOnly />
        </div>
        <div className="inspector-field">
          <label>Type</label>
          <input type="text" value={selectedNode.data.stateType} readOnly />
        </div>
        {selectedNode.data.isStart && (
          <div className="inspector-badge">Start State</div>
        )}
        <div className="inspector-separator" />
        <div className="inspector-section">
          <div className="inspector-section-title">State Data</div>
          <pre className="inspector-json">
            {JSON.stringify(stateData, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
