/**
 * RSF Graph Editor - Main Application.
 *
 * Two-panel layout: YAML editor (left) + graph canvas (right)
 * with palette sidebar and inspector panel.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';

import { useFlowStore } from './store/flowStore';
import { useWebSocket } from './sync/useWebSocket';
import { useYamlToGraphSync } from './sync/useYamlToGraphSync';
import { useGraphToYamlSync } from './sync/useGraphToYamlSync';

import { MonacoEditor } from './components/MonacoEditor';
import { GraphCanvas } from './components/GraphCanvas';
import { Palette } from './components/Palette';
import { Inspector } from './components/Inspector';
import { ValidationOverlay } from './components/ValidationOverlay';

import type { WSResponse, ParsedResponse } from './types';

function AppInner() {
  const [schema, setSchema] = useState<Record<string, unknown> | undefined>();
  const [connected, setConnected] = useState(false);

  const setYamlContent = useFlowStore((s) => s.setYamlContent);
  const setSyncSource = useFlowStore((s) => s.setSyncSource);

  const handleParsedRef = useRef<((r: ParsedResponse) => void) | null>(null);

  // WebSocket message handler
  const handleMessage = useCallback(
    (response: WSResponse) => {
      switch (response.type) {
        case 'parsed':
          handleParsedRef.current?.(response);
          break;
        case 'validated':
          useFlowStore.setState({ validationErrors: response.errors });
          break;
        case 'file_loaded':
          setSyncSource('editor');
          setYamlContent(response.yaml);
          break;
        case 'schema':
          setSchema(response.json_schema);
          break;
        case 'error':
          console.error('WebSocket error:', response.message);
          break;
      }
    },
    [setYamlContent, setSyncSource],
  );

  const { send } = useWebSocket({
    onMessage: handleMessage,
    onOpen: () => {
      setConnected(true);
      send({ type: 'get_schema' });
    },
    onClose: () => setConnected(false),
  });

  // YAML -> Graph sync
  const { handleParsedResponse } = useYamlToGraphSync({ send });

  useEffect(() => {
    handleParsedRef.current = handleParsedResponse;
  }, [handleParsedResponse]);

  // Graph -> YAML sync
  const { syncGraphToYaml } = useGraphToYamlSync({ send });

  return (
    <div className="app">
      <header className="app-header">
        <h1>RSF Graph Editor</h1>
        <span className={`connection-status ${connected ? 'connected' : ''}`}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </header>
      <div className="app-body">
        <Palette />
        <MonacoEditor schema={schema} />
        <GraphCanvas onGraphChange={syncGraphToYaml} />
        <Inspector />
      </div>
      <ValidationOverlay />
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppInner />
    </ReactFlowProvider>
  );
}
