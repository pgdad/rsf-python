/**
 * YAML -> Graph sync hook.
 *
 * Listens for YAML content changes, debounces 300ms, sends to backend
 * for parsing, converts AST to flow elements, and updates the store.
 * Uses syncSource pattern to prevent infinite loops.
 */

import { useEffect, useRef, useCallback } from 'react';
import { useFlowStore } from '../store/flowStore';
import { astToFlowElements } from './astToFlowElements';
import { getLayoutedElements } from '../layout/elkLayout';
import type { ParsedResponse } from '../types';

interface UseYamlToGraphSyncOptions {
  send: (message: { type: 'parse'; yaml: string }) => void;
}

export function useYamlToGraphSync({ send }: UseYamlToGraphSyncOptions) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const isFirstParse = useRef(true);

  const yamlContent = useFlowStore((s) => s.yamlContent);
  const syncSource = useFlowStore((s) => s.syncSource);
  const setSyncSource = useFlowStore((s) => s.setSyncSource);
  const updateFromAst = useFlowStore((s) => s.updateFromAst);

  // Debounced YAML parsing
  useEffect(() => {
    if (syncSource === 'graph') return;
    if (!yamlContent.trim()) return;

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      send({ type: 'parse', yaml: yamlContent });
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [yamlContent, syncSource, send]);

  // Handle parsed response from backend
  const handleParsedResponse = useCallback(
    async (response: ParsedResponse) => {
      if (syncSource === 'graph') {
        queueMicrotask(() => setSyncSource(null));
        return;
      }

      if (!response.ast) {
        useFlowStore.setState({ validationErrors: response.errors });
        return;
      }

      const existingNodes = useFlowStore.getState().nodes;
      const { nodes: newNodes, edges: newEdges } = astToFlowElements(
        response.ast,
        existingNodes,
      );

      const needsLayout =
        isFirstParse.current || newNodes.length !== existingNodes.length;

      if (needsLayout) {
        isFirstParse.current = false;
        const { nodes: layouted, edges: layoutedEdges } =
          await getLayoutedElements(newNodes, newEdges);
        updateFromAst(response.ast, response.errors, layouted, layoutedEdges);
      } else {
        updateFromAst(response.ast, response.errors, newNodes, newEdges);
      }

      queueMicrotask(() => setSyncSource(null));
    },
    [syncSource, setSyncSource, updateFromAst],
  );

  return { handleParsedResponse };
}
