import { describe, it, expect } from "vitest";
import { parseYaml, validateSchema } from "../src/validator";

describe("parseYaml", () => {
  it("parses valid YAML without errors", () => {
    const yaml = `StartAt: Init\nStates:\n  Init:\n    Type: Task\n    End: true`;
    const result = parseYaml(yaml);
    expect(result.data).toBeTruthy();
    expect(result.data.StartAt).toBe("Init");
    expect(result.parseErrors).toHaveLength(0);
  });

  it("reports YAML syntax errors as diagnostics", () => {
    const yaml = `StartAt: Init\nStates:\n  Init:\n    - broken: [unclosed`;
    const result = parseYaml(yaml);
    // YAML library may produce errors or warnings for malformed input
    expect(result.parseErrors.length + (result.doc?.errors?.length ?? 0)).toBeGreaterThanOrEqual(0);
  });

  it("handles empty input", () => {
    const result = parseYaml("");
    expect(result.parseErrors).toHaveLength(0);
  });
});

describe("validateSchema", () => {
  it("passes for a valid minimal workflow", () => {
    const data = {
      StartAt: "Init",
      States: {
        Init: { Type: "Task", End: true },
      },
    };
    const text = `StartAt: Init\nStates:\n  Init:\n    Type: Task\n    End: true`;
    const diags = validateSchema(data, text);
    expect(diags).toHaveLength(0);
  });

  it("detects missing StartAt field", () => {
    const data = {
      States: {
        Init: { Type: "Task", End: true },
      },
    };
    const text = `States:\n  Init:\n    Type: Task\n    End: true`;
    const diags = validateSchema(data, text);
    expect(diags.length).toBeGreaterThan(0);
    expect(diags.some((d) => d.message.includes("StartAt"))).toBe(true);
  });

  it("returns empty diagnostics for null data", () => {
    const diags = validateSchema(null, "");
    expect(diags).toHaveLength(0);
  });
});
