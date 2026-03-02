import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";
import { parseYaml, validateSchema } from "../src/validator";
import {
  validateSemantics,
  semanticErrorsToDiagnostics,
} from "../src/semanticValidator";
import { buildStateIndex, getDefinition, getReferences, getCompletions, getCodeActions } from "../src/stateNameProvider";
import { yamlToGraph, layoutGraph, applyErrorHighlights, extractErrorStateNames } from "../src/graphPreview";

const fixturesDir = path.join(__dirname, "fixtures");

function loadFixture(name: string): string {
  return fs.readFileSync(path.join(fixturesDir, name), "utf-8");
}

describe("Integration: Valid workflow", () => {
  const yaml = loadFixture("valid-workflow.yaml");

  it("produces 0 diagnostics from both schema and semantic validation", () => {
    const { data } = parseYaml(yaml);
    expect(data).toBeTruthy();

    const schemaDiags = validateSchema(data, yaml);
    const semanticErrors = validateSemantics(data);

    expect(schemaDiags).toHaveLength(0);
    expect(semanticErrors).toHaveLength(0);
  });

  it("builds correct state index with all definitions and references", () => {
    const index = buildStateIndex(yaml);
    expect(index.definitions.size).toBe(5);
    expect(index.references.length).toBeGreaterThanOrEqual(4);
  });

  it("generates graph with correct number of nodes and edges", () => {
    const { data } = parseYaml(yaml);
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(5);
    expect(graph.edges.length).toBeGreaterThanOrEqual(4);
  });
});

describe("Integration: Invalid references workflow", () => {
  const yaml = loadFixture("invalid-refs.yaml");

  it("produces semantic error for non-existent state reference", () => {
    const { data } = parseYaml(yaml);
    const semanticErrors = validateSemantics(data);

    const refError = semanticErrors.find((e) =>
      e.message.includes("NonExistentState")
    );
    expect(refError).toBeTruthy();
    expect(refError!.severity).toBe("error");
  });

  it("maps semantic errors to correct line positions", () => {
    const { data } = parseYaml(yaml);
    const semanticErrors = validateSemantics(data);
    const diags = semanticErrorsToDiagnostics(semanticErrors, yaml);

    expect(diags.length).toBeGreaterThan(0);
    // Each diagnostic should have valid line numbers
    for (const d of diags) {
      expect(d.range.start.line).toBeGreaterThanOrEqual(0);
    }
  });

  it("detects unreachable state (ProcessOrder is unreachable)", () => {
    const { data } = parseYaml(yaml);
    const errors = validateSemantics(data);
    const unreachable = errors.find(
      (e) =>
        e.message.includes("ProcessOrder") &&
        e.message.includes("not reachable")
    );
    expect(unreachable).toBeTruthy();
  });
});

describe("Integration: Unreachable states workflow", () => {
  const yaml = loadFixture("unreachable.yaml");

  it("flags OrphanState as unreachable", () => {
    const { data } = parseYaml(yaml);
    const errors = validateSemantics(data);
    const orphan = errors.find(
      (e) => e.message.includes("OrphanState")
    );
    expect(orphan).toBeTruthy();
  });
});

describe("Integration: Parallel workflow", () => {
  const yaml = loadFixture("parallel-workflow.yaml");

  it("validates successfully (no semantic errors)", () => {
    const { data } = parseYaml(yaml);
    const errors = validateSemantics(data);
    expect(errors).toHaveLength(0);
  });

  it("generates graph with 2 top-level nodes", () => {
    const { data } = parseYaml(yaml);
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(2);
  });
});

describe("Integration: Choice workflow", () => {
  const yaml = loadFixture("choice-workflow.yaml");

  it("validates successfully", () => {
    const { data } = parseYaml(yaml);
    const errors = validateSemantics(data);
    expect(errors).toHaveLength(0);
  });

  it("generates Choice edges for all branches", () => {
    const { data } = parseYaml(yaml);
    const graph = yamlToGraph(data);
    const routeEdges = graph.edges.filter(
      (e) => e.source === "RouteOrder"
    );
    expect(routeEdges.length).toBeGreaterThanOrEqual(2); // At least express + default
  });
});

describe("Integration: Go-to-definition end-to-end", () => {
  const yaml = loadFixture("valid-workflow.yaml");

  it("navigates from Next: ProcessOrder to ProcessOrder definition", () => {
    const index = buildStateIndex(yaml);
    const ref = index.references.find(
      (r) => r.stateName === "ProcessOrder" && r.field === "Next"
    );
    expect(ref).toBeTruthy();

    const def = getDefinition(index, "file:///workflow.yaml", {
      line: ref!.line,
      character: ref!.character,
    });
    expect(def).toBeTruthy();

    const loc = def as { uri: string; range: any };
    expect(loc.range.start.line).toBe(
      index.definitions.get("ProcessOrder")!.line
    );
  });
});

describe("Integration: Find All References end-to-end", () => {
  const yaml = loadFixture("valid-workflow.yaml");

  it("finds all locations referencing a state", () => {
    const index = buildStateIndex(yaml);
    const procDef = index.definitions.get("ProcessOrder")!;

    const refs = getReferences(index, "file:///workflow.yaml", {
      line: procDef.line,
      character: procDef.character,
    });
    expect(refs.length).toBeGreaterThanOrEqual(2); // definition + Next reference
  });
});

describe("Integration: Autocomplete end-to-end", () => {
  const yaml = loadFixture("valid-workflow.yaml");

  it("returns all state names in Next field position", () => {
    const index = buildStateIndex(yaml);
    const lines = yaml.split("\n");
    const nextLine = lines.findIndex((l) =>
      l.trim().startsWith("Next: ProcessOrder")
    );

    const completions = getCompletions(index, yaml, {
      line: nextLine,
      character: 10,
    });
    expect(completions.length).toBe(5);
  });
});

describe("Integration: Code Action for typo end-to-end", () => {
  it("suggests closest match for typo'd state name", () => {
    const yaml = `StartAt: ValidateInput
States:
  ValidateInput:
    Type: Task
    Next: ProcesOrder
  ProcessOrder:
    Type: Succeed`;

    const index = buildStateIndex(yaml);
    const typoRef = index.references.find(
      (r) => r.stateName === "ProcesOrder"
    );
    expect(typoRef).toBeTruthy();

    const actions = getCodeActions(index, {
      start: { line: typoRef!.line, character: 0 },
      end: { line: typoRef!.line, character: 50 },
    });
    expect(actions.some((a) => a.title.includes("ProcessOrder"))).toBe(true);
  });
});

describe("Integration: Graph + validator error highlights", () => {
  const yaml = loadFixture("invalid-refs.yaml");

  it("correctly identifies error nodes from validator output", () => {
    const { data } = parseYaml(yaml);
    const semanticErrors = validateSemantics(data);
    const diags = semanticErrorsToDiagnostics(semanticErrors, yaml);

    const errorNames = extractErrorStateNames(
      diags.map((d) => ({ message: d.message, source: d.source }))
    );

    const graph = yamlToGraph(data);
    const highlighted = applyErrorHighlights(graph, errorNames);

    // At least one node should have an error
    expect(highlighted.nodes.some((n) => n.hasError)).toBe(true);
  });
});

describe("Integration: Schema + semantic combined", () => {
  it("reports both schema and semantic errors", () => {
    const yaml = `States:
  Init:
    Type: Task
    Next: Ghost
    End: true`;
    // Missing StartAt (schema error) + Ghost reference (semantic error)

    const { data } = parseYaml(yaml);

    // Schema validation
    const schemaDiags = validateSchema(data, yaml);
    const schemaHasStartAtError = schemaDiags.some((d) =>
      d.message.includes("StartAt")
    );
    expect(schemaHasStartAtError).toBe(true);

    // Semantic validation
    const semanticErrors = validateSemantics(data);
    const hasGhostError = semanticErrors.some((e) =>
      e.message.includes("Ghost")
    );
    expect(hasGhostError).toBe(true);
  });
});
