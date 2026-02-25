/**
 * Graph → YAML sync hook.
 *
 * Watches for graph changes (node add/remove, edge changes),
 * merges them into the YAML using AST-merge strategy,
 * and sends the updated YAML to the backend for validation.
 */

import { useCallback } from 'react';
import { useFlowStore } from '../store/flowStore';
import { mergeGraphIntoYaml } from './mergeGraphIntoYaml';

interface UseGraphToYamlSyncOptions {
  send: (message: { type: 'parse'; yaml: string }) => void;
}

export function useGraphToYamlSync({ send }: UseGraphToYamlSyncOptions) {
  const syncGraphToYaml = useCallback(() => {
    const { syncSource, lastAst, nodes, edges, setSyncSource, setYamlContent } =
      useFlowStore.getState();

    // Prevent loopback: if editor initiated the change, don't sync back
    if (syncSource === 'editor') return;

    setSyncSource('graph');

    const yaml = mergeGraphIntoYaml(lastAst, nodes, edges);
    setYamlContent(yaml);

    // Send to backend for validation
    send({ type: 'parse', yaml });

    // Clear syncSource after microtask
    queueMicrotask(() => setSyncSource(null));
  }, [send]);

  return { syncGraphToYaml };
}
