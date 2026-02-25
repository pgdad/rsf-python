/**
 * Palette component with 8 state type buttons for drag-to-create.
 */

import type { DragEvent } from 'react';
import type { StateType } from '../types';

interface PaletteItem {
  type: StateType;
  icon: string;
  color: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'Task', icon: 'T', color: '#4a90d9' },
  { type: 'Pass', icon: 'P', color: '#7b68ee' },
  { type: 'Choice', icon: '?', color: '#e6a817' },
  { type: 'Wait', icon: 'W', color: '#9b59b6' },
  { type: 'Succeed', icon: '\u2713', color: '#27ae60' },
  { type: 'Fail', icon: '\u2717', color: '#e74c3c' },
  { type: 'Parallel', icon: '||', color: '#3498db' },
  { type: 'Map', icon: 'M', color: '#1abc9c' },
];

export function Palette() {
  const handleDragStart = (event: DragEvent, stateType: StateType) => {
    event.dataTransfer.setData('application/rsf-state-type', stateType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="palette">
      <div className="pane-header">States</div>
      <div className="palette-items">
        {PALETTE_ITEMS.map((item) => (
          <div
            key={item.type}
            className="palette-item"
            draggable
            onDragStart={(e) => handleDragStart(e, item.type)}
            style={{ borderLeftColor: item.color }}
          >
            <span
              className="palette-icon"
              style={{ backgroundColor: item.color }}
            >
              {item.icon}
            </span>
            <span className="palette-label">{item.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
