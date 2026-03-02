import { describe, it, expect } from "vitest";
import {
  yamlToGraph,
  layoutGraph,
  applyErrorHighlights,
  extractErrorStateNames,
} from "../src/graphPreview";

describe("yamlToGraph", () => {
  it("converts a 3-state workflow into nodes and edges", () => {
    const data = {
      StartAt: "A",
      States: {
        A: { Type: "Task", Next: "B" },
        B: { Type: "Choice", Choices: [{ Next: "C" }], Default: "C" },
        C: { Type: "Succeed" },
      },
    };
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(3);
    expect(graph.edges.length).toBeGreaterThanOrEqual(2);

    const nodeIds = graph.nodes.map((n) => n.id);
    expect(nodeIds).toContain("A");
    expect(nodeIds).toContain("B");
    expect(nodeIds).toContain("C");
  });

  it("handles Parallel state with branches", () => {
    const data = {
      StartAt: "P",
      States: {
        P: {
          Type: "Parallel",
          Branches: [
            { StartAt: "B1", States: { B1: { Type: "Task", End: true } } },
          ],
          Next: "Done",
        },
        Done: { Type: "Succeed" },
      },
    };
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(2); // P and Done (branches are nested)
    expect(graph.edges.some((e) => e.source === "P" && e.target === "Done")).toBe(true);
  });

  it("handles Choice state with multiple branches", () => {
    const data = {
      StartAt: "Route",
      States: {
        Route: {
          Type: "Choice",
          Choices: [
            { Variable: "$.x", StringEquals: "a", Next: "PathA" },
            { Variable: "$.x", StringEquals: "b", Next: "PathB" },
          ],
          Default: "PathC",
        },
        PathA: { Type: "Succeed" },
        PathB: { Type: "Succeed" },
        PathC: { Type: "Succeed" },
      },
    };
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(4);
    // Edges from Route to PathA, PathB, PathC
    const routeEdges = graph.edges.filter((e) => e.source === "Route");
    expect(routeEdges.length).toBeGreaterThanOrEqual(3);
  });

  it("returns empty graph for null data", () => {
    const graph = yamlToGraph(null);
    expect(graph.nodes).toHaveLength(0);
    expect(graph.edges).toHaveLength(0);
  });

  it("returns empty graph for data without States", () => {
    const graph = yamlToGraph({ StartAt: "X" });
    expect(graph.nodes).toHaveLength(0);
    expect(graph.edges).toHaveLength(0);
  });

  it("handles all 8 state types", () => {
    const data = {
      StartAt: "T",
      States: {
        T: { Type: "Task", Next: "P" },
        P: { Type: "Pass", Next: "W" },
        W: { Type: "Wait", Seconds: 5, Next: "C" },
        C: {
          Type: "Choice",
          Choices: [{ Next: "Pa" }],
          Default: "M",
        },
        Pa: { Type: "Parallel", Branches: [], Next: "M" },
        M: { Type: "Map", ItemProcessor: { StartAt: "X", States: {} }, Next: "S" },
        S: { Type: "Succeed" },
        F: { Type: "Fail" },
      },
    };
    const graph = yamlToGraph(data);
    expect(graph.nodes).toHaveLength(8);
    const types = graph.nodes.map((n) => n.type);
    expect(types).toContain("Task");
    expect(types).toContain("Pass");
    expect(types).toContain("Wait");
    expect(types).toContain("Choice");
    expect(types).toContain("Parallel");
    expect(types).toContain("Map");
    expect(types).toContain("Succeed");
    expect(types).toContain("Fail");
  });
});

describe("layoutGraph", () => {
  it("assigns non-overlapping positions to all nodes", () => {
    const data = {
      StartAt: "A",
      States: {
        A: { Type: "Task", Next: "B" },
        B: { Type: "Task", Next: "C" },
        C: { Type: "Succeed" },
      },
    };
    const graph = yamlToGraph(data);
    const laid = layoutGraph(graph);

    expect(laid.nodes).toHaveLength(3);
    // All nodes should have positions
    for (const node of laid.nodes) {
      expect(typeof node.x).toBe("number");
      expect(typeof node.y).toBe("number");
    }

    // Check non-overlapping (simple check: not all at same position)
    const positions = laid.nodes.map((n) => `${n.x},${n.y}`);
    const unique = new Set(positions);
    expect(unique.size).toBe(3);
  });

  it("handles empty graph", () => {
    const result = layoutGraph({ nodes: [], edges: [] });
    expect(result.nodes).toHaveLength(0);
  });
});

describe("applyErrorHighlights", () => {
  it("marks the correct nodes with errors", () => {
    const graphData = {
      nodes: [
        { id: "A", label: "A", type: "Task", x: 0, y: 0, width: 140, height: 50, hasError: false },
        { id: "B", label: "B", type: "Task", x: 0, y: 100, width: 140, height: 50, hasError: false },
        { id: "C", label: "C", type: "Succeed", x: 0, y: 200, width: 140, height: 50, hasError: false },
      ],
      edges: [],
    };
    const result = applyErrorHighlights(graphData, ["B"]);
    expect(result.nodes.find((n) => n.id === "A")!.hasError).toBe(false);
    expect(result.nodes.find((n) => n.id === "B")!.hasError).toBe(true);
    expect(result.nodes.find((n) => n.id === "C")!.hasError).toBe(false);
  });
});

describe("extractErrorStateNames", () => {
  it("extracts state names from diagnostic messages", () => {
    const errors = [
      { message: "State 'Orphan' is not reachable from StartAt" },
      { message: "Next 'Ghost' does not reference an existing state" },
    ];
    const names = extractErrorStateNames(errors);
    expect(names).toContain("Orphan");
    expect(names).toContain("Ghost");
  });
});
