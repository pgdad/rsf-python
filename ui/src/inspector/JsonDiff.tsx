/**
 * JsonDiff - Structural JSON diff between two objects.
 *
 * Uses flat path comparison to show added, removed, and changed fields
 * with color-coded output (green for added, red for removed, yellow for changed).
 */

import { useMemo } from 'react';

interface DiffEntry {
  path: string;
  type: 'added' | 'removed' | 'changed';
  oldValue?: string;
  newValue?: string;
}

/**
 * Flatten a nested object into dot-separated paths with string values.
 */
function flattenObject(
  obj: Record<string, unknown>,
  prefix = '',
): Record<string, string> {
  const result: Record<string, string> = {};

  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;

    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(result, flattenObject(value as Record<string, unknown>, path));
    } else {
      result[path] = JSON.stringify(value);
    }
  }

  return result;
}

/**
 * Compute structural diff between two flat path maps.
 */
function computeDiff(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): DiffEntry[] {
  const flatBefore = flattenObject(before);
  const flatAfter = flattenObject(after);
  const allPaths = new Set([
    ...Object.keys(flatBefore),
    ...Object.keys(flatAfter),
  ]);

  const entries: DiffEntry[] = [];

  for (const path of [...allPaths].sort()) {
    const inBefore = path in flatBefore;
    const inAfter = path in flatAfter;

    if (inBefore && !inAfter) {
      entries.push({ path, type: 'removed', oldValue: flatBefore[path] });
    } else if (!inBefore && inAfter) {
      entries.push({ path, type: 'added', newValue: flatAfter[path] });
    } else if (flatBefore[path] !== flatAfter[path]) {
      entries.push({
        path,
        type: 'changed',
        oldValue: flatBefore[path],
        newValue: flatAfter[path],
      });
    }
  }

  return entries;
}

const COLORS = {
  added: { bg: '#27ae6015', color: '#27ae60', prefix: '+' },
  removed: { bg: '#e74c3c15', color: '#e74c3c', prefix: '-' },
  changed: { bg: '#e6a81715', color: '#e6a817', prefix: '~' },
};

interface JsonDiffProps {
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export function JsonDiff({ before, after }: JsonDiffProps) {
  const entries = useMemo(() => computeDiff(before, after), [before, after]);

  if (entries.length === 0) {
    return <div className="json-diff-empty">No changes</div>;
  }

  return (
    <div className="json-diff">
      {entries.map((entry, i) => {
        const style = COLORS[entry.type];
        return (
          <div
            key={i}
            className="json-diff-entry"
            style={{ backgroundColor: style.bg }}
          >
            <span className="diff-prefix" style={{ color: style.color }}>
              {style.prefix}
            </span>
            <span className="diff-path">{entry.path}</span>
            {entry.type === 'removed' && (
              <span className="diff-value" style={{ color: style.color }}>
                {entry.oldValue}
              </span>
            )}
            {entry.type === 'added' && (
              <span className="diff-value" style={{ color: style.color }}>
                {entry.newValue}
              </span>
            )}
            {entry.type === 'changed' && (
              <>
                <span className="diff-value" style={{ color: '#e74c3c' }}>
                  {entry.oldValue}
                </span>
                <span className="diff-arrow">{'\u2192'}</span>
                <span className="diff-value" style={{ color: '#27ae60' }}>
                  {entry.newValue}
                </span>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
