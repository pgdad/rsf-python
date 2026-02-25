/**
 * YAML editor component using Monaco with monaco-yaml for
 * schema validation and autocompletion.
 */

import { useCallback } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { configureMonacoYaml } from 'monaco-yaml';
import { useFlowStore } from '../store/flowStore';

interface MonacoEditorProps {
  schemaUri?: string;
  schema?: Record<string, unknown>;
}

export function MonacoEditor({ schemaUri, schema }: MonacoEditorProps) {
  const yamlContent = useFlowStore((s) => s.yamlContent);
  const setYamlContent = useFlowStore((s) => s.setYamlContent);
  const setSyncSource = useFlowStore((s) => s.setSyncSource);
  const syncSource = useFlowStore((s) => s.syncSource);

  const handleMount: OnMount = useCallback(
    (_editor, monaco) => {
      const schemaConfig: Array<{
        uri: string;
        fileMatch: string[];
        schema?: Record<string, unknown>;
      }> = [];

      if (schema) {
        schemaConfig.push({
          uri: schemaUri ?? 'rsf-schema.json',
          fileMatch: ['*'],
          schema,
        });
      }

      configureMonacoYaml(monaco, {
        enableSchemaRequest: false,
        schemas: schemaConfig,
      });
    },
    [schema, schemaUri],
  );

  const handleChange = useCallback(
    (value: string | undefined) => {
      if (syncSource === 'graph') return;
      setSyncSource('editor');
      setYamlContent(value ?? '');
    },
    [syncSource, setSyncSource, setYamlContent],
  );

  return (
    <div className="editor-pane">
      <div className="pane-header">YAML Editor</div>
      <Editor
        height="100%"
        defaultLanguage="yaml"
        value={yamlContent}
        onChange={handleChange}
        onMount={handleMount}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          tabSize: 2,
          automaticLayout: true,
        }}
      />
    </div>
  );
}
