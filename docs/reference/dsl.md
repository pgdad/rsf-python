# DSL Reference

Complete field reference for the RSF workflow definition language. RSF achieves full feature parity with the Amazon States Language (ASL).

## Root Structure

Every RSF workflow starts with a root `StateMachineDefinition`:

```yaml
rsf_version: "1.0"
Comment: "Optional description"
StartAt: FirstState
QueryLanguage: JSONPath
TimeoutSeconds: 3600
Version: "1.0"
States:
  FirstState:
    Type: Task
    # ...
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rsf_version` | `string` | No | RSF format version. Default: `"1.0"` |
| `Comment` | `string` | No | Human-readable description |
| `StartAt` | `string` | **Yes** | Name of the first state to execute |
| `States` | `map<string, State>` | **Yes** | Map of state name to state definition |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Default query language. Default: `JSONPath` |
| `TimeoutSeconds` | `integer` (>= 0) | No | Maximum workflow execution duration |
| `Version` | `string` | No | User-defined version string |

## State Types

RSF supports all 8 ASL state types:

| Type | Purpose | Terminal? |
|------|---------|-----------|
| [Task](#task) | Execute a handler function | No |
| [Pass](#pass) | Pass input to output, optionally inject data | No |
| [Choice](#choice) | Branch based on conditions | No |
| [Wait](#wait) | Delay execution | No |
| [Parallel](#parallel) | Execute branches concurrently | No |
| [Map](#map) | Iterate over an array | No |
| [Succeed](#succeed) | Terminal success | Yes |
| [Fail](#fail) | Terminal failure | Yes |

---

### Task

Executes a handler function registered with `@state("StateName")`.

```yaml
ProcessOrder:
  Type: Task
  Comment: "Process the customer order"
  TimeoutSeconds: 300
  HeartbeatSeconds: 60
  InputPath: "$.order"
  Parameters:
    orderId.$: "$.id"
    staticValue: "constant"
  ResultSelector:
    processedId.$: "$.result.id"
  ResultPath: "$.processingResult"
  OutputPath: "$.processingResult"
  Retry:
    - ErrorEquals: ["ServiceUnavailable"]
      IntervalSeconds: 2
      MaxAttempts: 3
      BackoffRate: 2.0
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleError
      ResultPath: "$.error"
  Next: NextState
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Task"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Next` | `string` | **Yes*** | Next state to transition to |
| `End` | `boolean` | **Yes*** | Set to `true` to make this a terminal state |
| `TimeoutSeconds` | `integer` (>= 0) | No | Max execution time in seconds |
| `TimeoutSecondsPath` | `string` | No | JSONPath to timeout value (mutually exclusive with `TimeoutSeconds`) |
| `HeartbeatSeconds` | `integer` (>= 0) | No | Heartbeat interval (must be < `TimeoutSeconds`) |
| `HeartbeatSecondsPath` | `string` | No | JSONPath to heartbeat value (mutually exclusive with `HeartbeatSeconds`) |
| `Retry` | `list[RetryPolicy]` | No | Retry policies (see [Retry](#retry)) |
| `Catch` | `list[Catcher]` | No | Error catchers (see [Catch](#catch)) |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override default query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

*\* Must specify exactly one of `Next` or `End: true`*

**I/O Processing fields:** `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath` — see [I/O Pipeline](#io-pipeline).

---

### Pass

Passes input to output, optionally injecting a fixed `Result` value.

```yaml
InjectDefaults:
  Type: Pass
  Result:
    status: "pending"
    retries: 0
  ResultPath: "$.defaults"
  Next: ProcessOrder
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Pass"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Next` | `string` | **Yes*** | Next state |
| `End` | `boolean` | **Yes*** | Terminal state |
| `Result` | `any` | No | Fixed value to inject into the output |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

*\* Must specify exactly one of `Next` or `End: true`*

**I/O Processing fields:** `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`.

---

### Choice

Branches execution based on conditions evaluated against the input.

```yaml
CheckOrderType:
  Type: Choice
  Choices:
    - Variable: "$.total"
      NumericGreaterThan: 5000
      Next: HighValuePath
    - Variable: "$.status"
      StringEquals: "rush"
      Next: ExpressPath
  Default: StandardPath
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Choice"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Choices` | `list[ChoiceRule]` | **Yes** | Ordered list of choice rules |
| `Default` | `string` | No | State to transition to if no rule matches |
| `InputPath` | `string` | No | Filter input |
| `OutputPath` | `string` | No | Filter output |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

!!! note "No Next/End on Choice"
    Choice states do not have `Next` or `End` fields. Transitions are determined by the matching rule's `Next` field or the `Default` field.

#### Choice Rules

Each choice rule specifies a `Variable` (JSONPath), exactly one comparison operator, and a `Next` state.

**Data test rule:**

```yaml
- Variable: "$.amount"
  NumericGreaterThan: 100
  Next: HighValue
```

**Boolean combinators:**

```yaml
# AND — all conditions must match
- And:
    - Variable: "$.age"
      NumericGreaterThanEquals: 18
    - Variable: "$.country"
      StringEquals: "US"
  Next: EligibleUS

# OR — at least one must match
- Or:
    - Variable: "$.tier"
      StringEquals: "gold"
    - Variable: "$.tier"
      StringEquals: "platinum"
  Next: PremiumPath

# NOT — inverts the condition
- Not:
    Variable: "$.banned"
    BooleanEquals: true
  Next: AllowedPath
```

**JSONata condition rule:**

```yaml
- Condition: "$sum($.items.price) > 100"
  Next: HighValue
```

---

### Comparison Operators

RSF supports all 39 ASL comparison operators:

#### String Operators

| Operator | Value Type | Description |
|----------|-----------|-------------|
| `StringEquals` | `string` | Exact string equality |
| `StringEqualsPath` | `string` | Compare to value at JSONPath |
| `StringGreaterThan` | `string` | Lexicographic greater than |
| `StringGreaterThanPath` | `string` | Compare to value at JSONPath |
| `StringGreaterThanEquals` | `string` | Lexicographic greater than or equal |
| `StringGreaterThanEqualsPath` | `string` | Compare to value at JSONPath |
| `StringLessThan` | `string` | Lexicographic less than |
| `StringLessThanPath` | `string` | Compare to value at JSONPath |
| `StringLessThanEquals` | `string` | Lexicographic less than or equal |
| `StringLessThanEqualsPath` | `string` | Compare to value at JSONPath |
| `StringMatches` | `string` | Glob pattern match (`*` wildcard) |
| `StringMatchesPath` | `string` | Pattern from JSONPath |

#### Numeric Operators

| Operator | Value Type | Description |
|----------|-----------|-------------|
| `NumericEquals` | `number` | Numeric equality |
| `NumericEqualsPath` | `string` | Compare to value at JSONPath |
| `NumericGreaterThan` | `number` | Greater than |
| `NumericGreaterThanPath` | `string` | Compare to value at JSONPath |
| `NumericGreaterThanEquals` | `number` | Greater than or equal |
| `NumericGreaterThanEqualsPath` | `string` | Compare to value at JSONPath |
| `NumericLessThan` | `number` | Less than |
| `NumericLessThanPath` | `string` | Compare to value at JSONPath |
| `NumericLessThanEquals` | `number` | Less than or equal |
| `NumericLessThanEqualsPath` | `string` | Compare to value at JSONPath |

#### Boolean Operators

| Operator | Value Type | Description |
|----------|-----------|-------------|
| `BooleanEquals` | `boolean` | Boolean equality |
| `BooleanEqualsPath` | `string` | Compare to value at JSONPath |

#### Timestamp Operators

| Operator | Value Type | Description |
|----------|-----------|-------------|
| `TimestampEquals` | `string` | ISO 8601 timestamp equality |
| `TimestampEqualsPath` | `string` | Compare to value at JSONPath |
| `TimestampGreaterThan` | `string` | After timestamp |
| `TimestampGreaterThanPath` | `string` | Compare to value at JSONPath |
| `TimestampGreaterThanEquals` | `string` | At or after timestamp |
| `TimestampGreaterThanEqualsPath` | `string` | Compare to value at JSONPath |
| `TimestampLessThan` | `string` | Before timestamp |
| `TimestampLessThanPath` | `string` | Compare to value at JSONPath |
| `TimestampLessThanEquals` | `string` | At or before timestamp |
| `TimestampLessThanEqualsPath` | `string` | Compare to value at JSONPath |

#### Type Checking Operators

| Operator | Value Type | Description |
|----------|-----------|-------------|
| `IsBoolean` | `boolean` | `true` if Variable is a boolean |
| `IsNull` | `boolean` | `true` if Variable is null |
| `IsNumeric` | `boolean` | `true` if Variable is a number |
| `IsPresent` | `boolean` | `true` if Variable path exists |
| `IsString` | `boolean` | `true` if Variable is a string |
| `IsTimestamp` | `boolean` | `true` if Variable is an ISO 8601 timestamp |

---

### Wait

Delays execution for a specified duration or until a timestamp.

```yaml
# Wait a fixed number of seconds
WaitTenSeconds:
  Type: Wait
  Seconds: 10
  Next: Continue

# Wait until a specific timestamp
WaitUntilDeadline:
  Type: Wait
  Timestamp: "2026-03-01T00:00:00Z"
  Next: Continue

# Wait duration from input
WaitDynamic:
  Type: Wait
  SecondsPath: "$.waitTime"
  Next: Continue

# Wait until timestamp from input
WaitUntilDynamic:
  Type: Wait
  TimestampPath: "$.deadline"
  Next: Continue
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Wait"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Next` | `string` | **Yes*** | Next state |
| `End` | `boolean` | **Yes*** | Terminal state |
| `Seconds` | `integer` (>= 0) | **One of four** | Fixed wait duration |
| `Timestamp` | `string` | **One of four** | ISO 8601 absolute timestamp |
| `SecondsPath` | `string` | **One of four** | JSONPath to seconds value |
| `TimestampPath` | `string` | **One of four** | JSONPath to timestamp value |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

*\* Must specify exactly one of `Next` or `End: true`*

!!! warning "Exactly one timing specification"
    Wait states must specify exactly one of `Seconds`, `Timestamp`, `SecondsPath`, or `TimestampPath`.

**I/O Processing fields:** `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`.

---

### Parallel

Executes multiple branches concurrently. All branches must complete successfully for the Parallel state to succeed.

```yaml
ProcessInParallel:
  Type: Parallel
  Branches:
    - StartAt: ProcessPayment
      States:
        ProcessPayment:
          Type: Task
          End: true
    - StartAt: ReserveInventory
      States:
        ReserveInventory:
          Type: Task
          End: true
    - StartAt: SendNotification
      States:
        SendNotification:
          Type: Task
          End: true
  ResultPath: "$.parallelResults"
  Retry:
    - ErrorEquals: ["States.ALL"]
      MaxAttempts: 2
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleError
  Next: Finalize
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Parallel"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Branches` | `list[BranchDefinition]` | **Yes** | Concurrent branches to execute |
| `Next` | `string` | **Yes*** | Next state |
| `End` | `boolean` | **Yes*** | Terminal state |
| `Retry` | `list[RetryPolicy]` | No | Retry policies |
| `Catch` | `list[Catcher]` | No | Error catchers |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

*\* Must specify exactly one of `Next` or `End: true`*

**I/O Processing fields:** `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`.

#### BranchDefinition

Each branch is a sub-state machine:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `StartAt` | `string` | **Yes** | First state in the branch |
| `States` | `map<string, State>` | **Yes** | States in this branch |
| `Comment` | `string` | No | Description |
| `ProcessorConfig` | `ProcessorConfig` | No | Processing mode |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Query language |

---

### Map

Iterates over an array, executing a sub-state machine for each element.

```yaml
ProcessItems:
  Type: Map
  ItemsPath: "$.orderItems"
  MaxConcurrency: 10
  ItemSelector:
    item.$: "$$.Map.Item.Value"
    index.$: "$$.Map.Item.Index"
  ItemProcessor:
    StartAt: ProcessItem
    States:
      ProcessItem:
        Type: Task
        End: true
  ResultPath: "$.processedItems"
  Retry:
    - ErrorEquals: ["States.ALL"]
      MaxAttempts: 2
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleError
  Next: Finalize
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Map"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `ItemProcessor` | `BranchDefinition` | No | Sub-state machine for each item |
| `ItemsPath` | `string` | No | JSONPath to the input array. Default: `$` (entire input) |
| `MaxConcurrency` | `integer` (>= 0) | No | Max concurrent iterations. `0` = unlimited |
| `ItemSelector` | `map<string, any>` | No | Transform each item before processing |
| `Next` | `string` | **Yes*** | Next state |
| `End` | `boolean` | **Yes*** | Terminal state |
| `Retry` | `list[RetryPolicy]` | No | Retry policies |
| `Catch` | `list[Catcher]` | No | Error catchers |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

*\* Must specify exactly one of `Next` or `End: true`*

**I/O Processing fields:** `InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`.

---

### Succeed

Terminal state indicating successful completion.

```yaml
OrderComplete:
  Type: Succeed
  Comment: "Order processed successfully"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Succeed"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `InputPath` | `string` | No | Filter input |
| `OutputPath` | `string` | No | Filter output |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |
| `Assign` | `map<string, any>` | No | Variables to assign |
| `Output` | `any` | No | Output expression |

---

### Fail

Terminal state indicating failure with an error name and cause.

```yaml
OrderFailed:
  Type: Fail
  Error: "OrderProcessingFailed"
  Cause: "Payment was declined"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `Type` | `"Fail"` | **Yes** | State type identifier |
| `Comment` | `string` | No | Description |
| `Error` | `string` | No | Error name |
| `ErrorPath` | `string` | No | JSONPath to error name (mutually exclusive with `Error`) |
| `Cause` | `string` | No | Human-readable error cause |
| `CausePath` | `string` | No | JSONPath to cause (mutually exclusive with `Cause`) |
| `QueryLanguage` | `"JSONPath"` \| `"JSONata"` | No | Override query language |

!!! note "No I/O processing on Fail"
    Fail states do not support I/O processing fields (`InputPath`, `OutputPath`, `Parameters`, `ResultSelector`, `ResultPath`). This matches the ASL specification.

---

## I/O Pipeline

RSF implements the full 5-stage ASL I/O processing pipeline. Each stage transforms data as it flows through a state:

```
Input → InputPath → Parameters → [State Logic] → ResultSelector → ResultPath → OutputPath → Output
```

| Stage | Field | Description |
|-------|-------|-------------|
| 1 | `InputPath` | JSONPath to filter the state input. Default: `"$"` (entire input) |
| 2 | `Parameters` | Construct a new JSON object from the filtered input. Fields ending in `.$` are evaluated as JSONPath |
| 3 | `ResultSelector` | Filter the state's raw result. Fields ending in `.$` are evaluated as JSONPath against the result |
| 4 | `ResultPath` | JSONPath specifying where to place the (optionally selected) result in the original input. Default: `"$"` (replace entire input) |
| 5 | `OutputPath` | JSONPath to filter the combined result. Default: `"$"` (entire output) |

### Example

```yaml
FilterAndTransform:
  Type: Task
  InputPath: "$.order"
  Parameters:
    orderId.$: "$.id"
    customerId.$: "$.customer.id"
    staticValue: "constant"
  ResultSelector:
    processedId.$: "$.result.id"
    status.$: "$.result.status"
  ResultPath: "$.processingResult"
  OutputPath: "$.processingResult"
  Next: Done
```

**Supported on:** Task, Pass, Wait, Parallel, Map (all states except Choice, Succeed, and Fail).

---

## Error Handling

### Retry

Retry policies define automatic retry behavior with exponential backoff.

```yaml
Retry:
  - ErrorEquals: ["ServiceUnavailable"]
    IntervalSeconds: 1
    MaxAttempts: 3
    BackoffRate: 2.0
  - ErrorEquals: ["RateLimitExceeded"]
    IntervalSeconds: 5
    MaxAttempts: 5
    BackoffRate: 1.5
    MaxDelaySeconds: 30
    JitterStrategy: FULL
  - ErrorEquals: ["States.ALL"]
    MaxAttempts: 1
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `ErrorEquals` | `list[string]` | **Yes** | — | Error names to match |
| `IntervalSeconds` | `integer` (>= 0) | No | `1` | Initial retry delay |
| `MaxAttempts` | `integer` (>= 0) | No | `3` | Maximum retry count |
| `BackoffRate` | `float` (>= 1.0) | No | `2.0` | Multiplier for each subsequent delay |
| `MaxDelaySeconds` | `integer` (>= 0) | No | — | Cap on retry delay |
| `JitterStrategy` | `"FULL"` \| `"NONE"` | No | — | Add randomness to retry delays |

**Built-in error names:**

- `States.ALL` — Matches all errors
- `States.Timeout` — Task exceeded `TimeoutSeconds`
- `States.TaskFailed` — Task threw an unhandled exception
- `States.Permissions` — IAM permission error

### Catch

Catchers route errors to recovery states.

```yaml
Catch:
  - ErrorEquals: ["ValidationError"]
    Next: HandleValidation
    ResultPath: "$.validationError"
  - ErrorEquals: ["States.ALL"]
    Next: CatchAll
    ResultPath: "$.error"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ErrorEquals` | `list[string]` | **Yes** | Error names to match |
| `Next` | `string` | **Yes** | State to transition to |
| `ResultPath` | `string` | No | Where to place the error in the state input |
| `Comment` | `string` | No | Description |

**Supported on:** Task, Parallel, Map.

---

## Intrinsic Functions

RSF supports all 18 ASL intrinsic functions. Use them in `Parameters` and `ResultSelector` fields with the `.$` suffix:

```yaml
Parameters:
  id.$: "States.Format('ORDER-{}', $.orderId)"
  items.$: "States.Array($.item1, $.item2, $.item3)"
```

### String Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.Format` | `(template, ...args) → string` | String interpolation with `{}` placeholders |
| `States.StringSplit` | `(string, delimiter) → list[string]` | Split string by delimiter |

### Array Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.Array` | `(...items) → list` | Create array from arguments |
| `States.ArrayPartition` | `(array, size) → list[list]` | Split array into chunks |
| `States.ArrayContains` | `(array, value) → boolean` | Check if array contains value |
| `States.ArrayRange` | `(start, end, step) → list[int]` | Generate numeric range (inclusive) |
| `States.ArrayGetItem` | `(array, index) → any` | Get array element by index |
| `States.ArrayLength` | `(array) → integer` | Return array length |
| `States.ArrayUnique` | `(array) → list` | Deduplicate array, preserving order |

### JSON Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.StringToJson` | `(string) → any` | Parse JSON string |
| `States.JsonToString` | `(value) → string` | Serialize value to JSON string |

### Math Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.MathRandom` | `(start, end) → integer` | Random integer in [start, end] |
| `States.MathAdd` | `(a, b) → number` | Add two numbers |

### Encoding Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.Base64Encode` | `(string) → string` | Base64 encode |
| `States.Base64Decode` | `(string) → string` | Base64 decode |
| `States.Hash` | `(data, algorithm) → string` | Hash with SHA-1, SHA-256, SHA-384, SHA-512, or MD5 |

### Utility Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `States.UUID` | `() → string` | Generate UUID v4 |

---

## Variables

RSF supports workflow variables via `Assign` and `Output` fields, available on Task, Pass, Choice, Wait, Parallel, Map, and Succeed states.

### Assign

Set variables that persist across state transitions:

```yaml
SetCounters:
  Type: Pass
  Assign:
    retryCount: 0
    maxRetries: 3
  Next: ProcessItem
```

### Output

Define an output expression:

```yaml
TransformResult:
  Type: Task
  Output:
    summary.$: "$.result"
    timestamp.$: "$$.State.EnteredTime"
  Next: Done
```

---

## Context Object

Access execution metadata via the context object (`$$`):

| Path | Description |
|------|-------------|
| `$$.Execution.Id` | Execution ID |
| `$$.Execution.Name` | Execution name |
| `$$.Execution.StartTime` | Execution start timestamp |
| `$$.State.Name` | Current state name |
| `$$.State.EnteredTime` | When the current state was entered |
| `$$.Map.Item.Index` | Current Map iteration index |
| `$$.Map.Item.Value` | Current Map iteration value |

Use in `Parameters` with the `.$` suffix:

```yaml
Parameters:
  executionId.$: "$$.Execution.Id"
  stateName.$: "$$.State.Name"
  itemIndex.$: "$$.Map.Item.Index"
```
