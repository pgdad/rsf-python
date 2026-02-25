/**
 * TypeScript type definitions for the RSF Graph Editor.
 */

import type { Node, Edge } from '@xyflow/react';

/** The 8 ASL state types */
export type StateType =
  | 'Task'
  | 'Pass'
  | 'Choice'
  | 'Wait'
  | 'Succeed'
  | 'Fail'
  | 'Parallel'
  | 'Map';

/** Data carried by every flow node */
export type FlowNodeData = {
  label: string;
  stateType: StateType;
  isStart?: boolean;
  /** Raw state definition from the AST */
  stateData?: Record<string, unknown>;
  /** Validation errors on this node */
  errors?: ValidationError[];
  [key: string]: unknown;
};

/** Typed xyflow node */
export type FlowNode = Node<FlowNodeData>;

/** Data carried by transition edges */
export type FlowEdgeData = {
  edgeType?: 'normal' | 'catch' | 'default' | 'choice';
  label?: string;
  [key: string]: unknown;
};

/** Typed xyflow edge */
export type FlowEdge = Edge<FlowEdgeData>;

/** Validation error from the backend */
export interface ValidationError {
  message: string;
  path: string;
  severity: 'error' | 'warning';
}

/** Parsed AST from the backend */
export interface ParsedResponse {
  type: 'parsed';
  ast: Record<string, unknown> | null;
  yaml: string;
  errors: ValidationError[];
}

/** Validation-only response */
export interface ValidatedResponse {
  type: 'validated';
  errors: ValidationError[];
}

/** File loaded response */
export interface FileLoadedResponse {
  type: 'file_loaded';
  yaml: string;
  path: string;
}

/** File saved response */
export interface FileSavedResponse {
  type: 'file_saved';
  path: string;
}

/** Schema response */
export interface SchemaResponse {
  type: 'schema';
  json_schema: Record<string, unknown>;
}

/** Error response */
export interface ErrorResponse {
  type: 'error';
  message: string;
}

/** All possible WebSocket response types */
export type WSResponse =
  | ParsedResponse
  | ValidatedResponse
  | FileLoadedResponse
  | FileSavedResponse
  | SchemaResponse
  | ErrorResponse;

/** WebSocket outgoing message types */
export interface ParseMessage {
  type: 'parse';
  yaml: string;
}

export interface ValidateMessage {
  type: 'validate';
  yaml: string;
}

export interface LoadFileMessage {
  type: 'load_file';
  path: string;
}

export interface SaveFileMessage {
  type: 'save_file';
  path: string;
  yaml: string;
}

export interface GetSchemaMessage {
  type: 'get_schema';
}

export type WSMessage =
  | ParseMessage
  | ValidateMessage
  | LoadFileMessage
  | SaveFileMessage
  | GetSchemaMessage;

/** Sync source for preventing infinite loops */
export type SyncSource = 'editor' | 'graph' | null;
