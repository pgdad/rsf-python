/**
 * Base node component shared by all state type nodes.
 * Provides consistent layout with handles, label, and type badge.
 * Includes expand/collapse chevron and expanded content panel.
 */

import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { FlowNode } from '../types';
import { useFlowStore } from '../store/flowStore';

interface BaseNodeProps {
  nodeProps: NodeProps<FlowNode>;
  color: string;
  icon: string;
  children?: React.ReactNode;
  expandedContent?: React.ReactNode;
}

export function BaseNode({ nodeProps, color, icon, children, expandedContent }: BaseNodeProps) {
  const { id, data, selected } = nodeProps;
  const selectNode = useFlowStore((s) => s.selectNode);
  const expandedNodeId = useFlowStore((s) => s.expandedNodeId);
  const toggleExpand = useFlowStore((s) => s.toggleExpand);
  const isExpanded = expandedNodeId === id;
  const hasErrors = data.errors && data.errors.length > 0;

  return (
    <div
      className={`flow-node ${selected ? 'selected' : ''} ${hasErrors ? 'has-errors' : ''} ${isExpanded ? 'expanded' : ''}`}
      style={{ borderColor: color }}
      onClick={() => selectNode(id)}
    >
      <Handle type="target" position={Position.Top} />
      <div className="node-header" style={{ backgroundColor: color }}>
        <span className="node-icon">{icon}</span>
        <span className="node-type">{data.stateType}</span>
        {data.isStart && <span className="node-start-badge">START</span>}
        <button
          className="node-expand-chevron"
          onClick={(e) => { e.stopPropagation(); toggleExpand(id); }}
          title={isExpanded ? 'Collapse' : 'Expand'}
        >
          {isExpanded ? '\u25B2' : '\u25BC'}
        </button>
      </div>
      <div className="node-body">
        <div className="node-label">{data.label}</div>
        {children}
        {isExpanded && (
          <div className="node-expanded-panel">
            {expandedContent || <div className="node-expanded-placeholder">Properties</div>}
          </div>
        )}
      </div>
      {hasErrors && (
        <div className="node-error-badge" title={data.errors![0].message}>
          {data.errors!.length}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
