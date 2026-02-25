/**
 * RSF Application - Main entry point.
 *
 * Hash-based routing:
 * - #/editor  → Graph Editor (default)
 * - #/inspector → Execution Inspector
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
import { InspectorApp } from './inspector/InspectorApp';

import type { WSResponse, ParsedResponse } from './types';

type AppRoute = 'editor' | 'inspector';

function useHashRoute(): AppRoute {
  const [route, setRoute] = useState<AppRoute>(() => {
    const hash = window.location.hash;
    if (hash === '#/inspector') return 'inspector';
    return 'editor';
  });

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash;
      if (hash === '#/inspector') setRoute('inspector');
      else setRoute('editor');
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  return route;
}

function EditorApp() {
  const [schema, setSchema] = useState<Record<string, unknown> | undefined>();
  const [connected, setConnected] = useState(false);

  const setYamlContent = useFlowStore((s) => s.setYamlContent);
  const setSyncSource = useFlowStore((s) => s.setSyncSource);

  const handleParsedRef = useRef<((r: ParsedResponse) => void) | null>(null);

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

  const { handleParsedResponse } = useYamlToGraphSync({ send });

  useEffect(() => {
    handleParsedRef.current = handleParsedResponse;
  }, [handleParsedResponse]);

  const { syncGraphToYaml } = useGraphToYamlSync({ send });

  return (
    <div className="app">
      <header className="app-header">
        <h1>RSF Graph Editor</h1>
        <div className="header-right">
          <a href="#/inspector" className="header-link">Inspector</a>
          <span className={`connection-status ${connected ? 'connected' : ''}`}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
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
  const route = useHashRoute();

  if (route === 'inspector') {
    return (
      <ReactFlowProvider>
        <InspectorApp />
      </ReactFlowProvider>
    );
  }

  return (
    <ReactFlowProvider>
      <EditorApp />
    </ReactFlowProvider>
  );
}
