import { describe, it, expect } from "vitest";
import { validateSemantics } from "../src/semanticValidator";

describe("validateSemantics", () => {
  it("returns no errors for a valid workflow", () => {
    const data = {
      StartAt: "Init",
      States: {
        Init: { Type: "Task", Next: "Done" },
        Done: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    expect(errors).toHaveLength(0);
  });

  it("detects non-existent state reference in Next", () => {
    const data = {
      StartAt: "Init",
      States: {
        Init: { Type: "Task", Next: "NonExistent" },
        Done: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    const refError = errors.find((e) =>
      e.message.includes("NonExistent")
    );
    expect(refError).toBeTruthy();
    expect(refError!.severity).toBe("error");
  });

  it("detects unreachable state", () => {
    const data = {
      StartAt: "Init",
      States: {
        Init: { Type: "Task", End: true },
        Orphan: { Type: "Task", End: true },
      },
    };
    const errors = validateSemantics(data);
    const unreachable = errors.find((e) =>
      e.message.includes("not reachable")
    );
    expect(unreachable).toBeTruthy();
    expect(unreachable!.message).toContain("Orphan");
  });

  it("detects missing terminal state", () => {
    const data = {
      StartAt: "A",
      States: {
        A: { Type: "Task", Next: "B" },
        B: { Type: "Task", Next: "A" },
      },
    };
    const errors = validateSemantics(data);
    const terminal = errors.find((e) =>
      e.message.includes("terminal state")
    );
    expect(terminal).toBeTruthy();
  });

  it("detects States.ALL not last in Catch", () => {
    const data = {
      StartAt: "Init",
      States: {
        Init: {
          Type: "Task",
          Next: "Done",
          Catch: [
            { ErrorEquals: ["States.ALL"], Next: "Done" },
            { ErrorEquals: ["CustomError"], Next: "Done" },
          ],
        },
        Done: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    const allOrder = errors.find((e) =>
      e.message.includes("States.ALL")
    );
    expect(allOrder).toBeTruthy();
  });

  it("detects StartAt referencing non-existent state", () => {
    const data = {
      StartAt: "Missing",
      States: {
        Init: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    const startErr = errors.find((e) =>
      e.message.includes("StartAt") && e.message.includes("Missing")
    );
    expect(startErr).toBeTruthy();
  });

  it("validates Parallel branch states recursively", () => {
    const data = {
      StartAt: "Para",
      States: {
        Para: {
          Type: "Parallel",
          Branches: [
            {
              StartAt: "B1",
              States: {
                B1: { Type: "Task", Next: "Ghost" },
              },
            },
          ],
          End: true,
        },
      },
    };
    const errors = validateSemantics(data);
    const branchErr = errors.find(
      (e) =>
        e.message.includes("Ghost") &&
        e.message.includes("does not reference")
    );
    expect(branchErr).toBeTruthy();
  });

  it("warns when TimeoutSeconds exceeds 30 days", () => {
    const data = {
      StartAt: "Init",
      TimeoutSeconds: 3000000,
      States: {
        Init: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    const timeoutWarn = errors.find((e) =>
      e.message.includes("30 days")
    );
    expect(timeoutWarn).toBeTruthy();
    expect(timeoutWarn!.severity).toBe("warning");
  });

  it("handles null/undefined data gracefully", () => {
    expect(validateSemantics(null)).toHaveLength(0);
    expect(validateSemantics(undefined)).toHaveLength(0);
  });

  it("validates Choice state Default reference", () => {
    const data = {
      StartAt: "Check",
      States: {
        Check: {
          Type: "Choice",
          Choices: [
            {
              Variable: "$.x",
              StringEquals: "a",
              Next: "Done",
            },
          ],
          Default: "NonExistent",
        },
        Done: { Type: "Succeed" },
      },
    };
    const errors = validateSemantics(data);
    const defaultErr = errors.find((e) =>
      e.message.includes("Default") && e.message.includes("NonExistent")
    );
    expect(defaultErr).toBeTruthy();
  });
});
