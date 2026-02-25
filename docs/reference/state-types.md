# State Types Guide

Detailed examples for each RSF state type, showing YAML definitions alongside the generated Python code.

## Task State

The Task state executes a handler function. It's the workhorse of RSF workflows — any state that needs to run business logic uses Task.

### Basic Task

=== "YAML"

    ```yaml
    rsf_version: "1.0"
    StartAt: ProcessOrder
    States:
      ProcessOrder:
        Type: Task
        Next: Done
      Done:
        Type: Succeed
    ```

=== "Generated Handler"

    ```python
    from rsf.registry import state

    @state("ProcessOrder")
    def handle(event, context):
        # TODO: Implement ProcessOrder logic
        return event
    ```

### Task with I/O Processing

=== "YAML"

    ```yaml
    FilterInput:
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
      Next: NextStep
    ```

=== "Handler"

    ```python
    @state("FilterInput")
    def handle(event, context):
        # event = {"orderId": "...", "customerId": "...", "staticValue": "constant"}
        # (filtered by InputPath, then transformed by Parameters)
        result = process(event["orderId"])
        return {"result": {"id": result.id, "status": result.status}}
        # ResultSelector picks processedId and status
        # ResultPath places result at $.processingResult in original input
    ```

### Task with Retry and Catch

```yaml
CallExternalService:
  Type: Task
  TimeoutSeconds: 300
  HeartbeatSeconds: 60
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
  Catch:
    - ErrorEquals: ["ServiceUnavailable"]
      Next: FallbackHandler
      ResultPath: "$.serviceError"
    - ErrorEquals: ["States.ALL"]
      Next: CatchAll
      ResultPath: "$.error"
  Next: Done
```

Retry policies are evaluated in order. The first matching `ErrorEquals` is used. If all retries are exhausted, Catch handlers are evaluated in order.

---

## Pass State

Pass states inject data, transform input, or act as placeholder states.

### Inject a fixed result

```yaml
SetDefaults:
  Type: Pass
  Result:
    status: "pending"
    retries: 0
    createdAt: "2026-01-01T00:00:00Z"
  ResultPath: "$.defaults"
  Next: ProcessOrder
```

### Transform input with Parameters

```yaml
ExtractFields:
  Type: Pass
  Parameters:
    orderId.$: "$.order.id"
    items.$: "$.order.items"
    total.$: "$.order.total"
  ResultPath: "$.validated"
  Next: CheckOrder
```

---

## Choice State

Choice states evaluate conditions and branch accordingly. Each rule specifies a `Variable` (JSONPath reference), a comparison operator, and a `Next` state.

### Simple branching

```yaml
CheckOrderType:
  Type: Choice
  Choices:
    - Variable: "$.validated.total"
      NumericGreaterThan: 5000
      Next: HighValueApproval
    - Variable: "$.validated.total"
      NumericLessThanEquals: 0
      Next: OrderRejected
  Default: StandardProcessing
```

### Boolean combinators

```yaml
CheckEligibility:
  Type: Choice
  Choices:
    - And:
        - Variable: "$.age"
          NumericGreaterThanEquals: 18
        - Variable: "$.country"
          StringEquals: "US"
        - Not:
            Variable: "$.banned"
            BooleanEquals: true
      Next: Eligible
    - Or:
        - Variable: "$.tier"
          StringEquals: "gold"
        - Variable: "$.tier"
          StringEquals: "platinum"
      Next: PremiumPath
  Default: StandardPath
```

### Type checking

```yaml
ValidateInput:
  Type: Choice
  Choices:
    - Variable: "$.email"
      IsPresent: true
      Next: HasEmail
    - Variable: "$.email"
      IsNull: true
      Next: RequestEmail
  Default: RequestEmail
```

---

## Wait State

Wait states introduce delays — useful for polling, rate limiting, or scheduling.

### Fixed delay

```yaml
WaitBeforeRetry:
  Type: Wait
  Seconds: 30
  Next: RetryOperation
```

### Wait until a timestamp

```yaml
WaitForDeadline:
  Type: Wait
  Timestamp: "2026-12-31T23:59:59Z"
  Next: ExecuteAtMidnight
```

### Dynamic delay from input

```yaml
WaitDynamic:
  Type: Wait
  SecondsPath: "$.backoffSeconds"
  Next: RetryOperation
```

### Dynamic timestamp from input

```yaml
WaitUntilScheduled:
  Type: Wait
  TimestampPath: "$.scheduledTime"
  Next: Execute
```

---

## Parallel State

Parallel states run multiple branches concurrently. The output is an array of branch results (one element per branch, in order).

### Basic parallel execution

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
    - StartAt: SendConfirmation
      States:
        SendConfirmation:
          Type: Task
          End: true
  ResultPath: "$.parallelResults"
  Next: Finalize
```

Output: `$.parallelResults` contains `[paymentResult, inventoryResult, confirmationResult]`.

### Parallel with error handling

```yaml
ParallelWithRecovery:
  Type: Parallel
  Branches:
    - StartAt: Branch1
      States:
        Branch1:
          Type: Task
          End: true
    - StartAt: Branch2
      States:
        Branch2:
          Type: Task
          End: true
  Retry:
    - ErrorEquals: ["States.ALL"]
      MaxAttempts: 2
  Catch:
    - ErrorEquals: ["States.ALL"]
      Next: HandleParallelFailure
      ResultPath: "$.parallelError"
  Next: Done
```

### Nested parallel

Branches can contain any state types, including nested Parallel or Map states:

```yaml
OuterParallel:
  Type: Parallel
  Branches:
    - StartAt: InnerParallel
      States:
        InnerParallel:
          Type: Parallel
          Branches:
            - StartAt: DeepTask1
              States:
                DeepTask1:
                  Type: Task
                  End: true
            - StartAt: DeepTask2
              States:
                DeepTask2:
                  Type: Task
                  End: true
          End: true
  Next: Done
```

---

## Map State

Map states iterate over an array, running a sub-state machine for each element. The output is an array of results from each iteration.

### Basic iteration

```yaml
ProcessItems:
  Type: Map
  ItemsPath: "$.orderItems"
  ItemProcessor:
    StartAt: ProcessItem
    States:
      ProcessItem:
        Type: Task
        End: true
  ResultPath: "$.processedItems"
  Next: Finalize
```

### With concurrency limit and item selector

```yaml
ProcessItemsControlled:
  Type: Map
  ItemsPath: "$.items"
  MaxConcurrency: 5
  ItemSelector:
    item.$: "$$.Map.Item.Value"
    index.$: "$$.Map.Item.Index"
    orderId.$: "$.orderId"
  ItemProcessor:
    StartAt: EnrichItem
    States:
      EnrichItem:
        Type: Task
        Next: ValidateItem
      ValidateItem:
        Type: Task
        End: true
  ResultPath: "$.enrichedItems"
  Next: Done
```

### Nested Map

```yaml
ProcessCategories:
  Type: Map
  ItemsPath: "$.categories"
  ItemProcessor:
    StartAt: ProcessCategory
    States:
      ProcessCategory:
        Type: Map
        ItemsPath: "$.items"
        ItemProcessor:
          StartAt: ProcessCategoryItem
          States:
            ProcessCategoryItem:
              Type: Task
              End: true
        End: true
  Next: Done
```

---

## Succeed State

Terminal state indicating successful completion. Optionally filters output.

```yaml
OrderComplete:
  Type: Succeed
  Comment: "Order successfully processed"
  InputPath: "$.summary"
  OutputPath: "$.result"
```

---

## Fail State

Terminal state indicating failure. Reports an error name and human-readable cause.

### Static error

```yaml
OrderFailed:
  Type: Fail
  Error: "OrderProcessingFailed"
  Cause: "Payment was declined"
```

### Dynamic error from input

```yaml
DynamicFailure:
  Type: Fail
  ErrorPath: "$.errorCode"
  CausePath: "$.errorMessage"
```

!!! note "Mutual exclusion"
    `Error` and `ErrorPath` are mutually exclusive. Same for `Cause` and `CausePath`. You cannot specify both static and dynamic values.

---

## Complete Example

A real-world order processing workflow using all major state types:

```yaml
rsf_version: "1.0"
Comment: "Multi-state order processing workflow"
StartAt: ReceiveOrder
States:
  ReceiveOrder:
    Type: Task
    ResultPath: "$.order"
    Next: ValidateOrder

  ValidateOrder:
    Type: Pass
    Parameters:
      orderId.$: "$.order.id"
      items.$: "$.order.items"
      total.$: "$.order.total"
    ResultPath: "$.validated"
    Next: CheckOrderType

  CheckOrderType:
    Type: Choice
    Choices:
      - Variable: "$.validated.total"
        NumericGreaterThan: 5000
        Next: HighValueApproval
      - Variable: "$.validated.total"
        NumericLessThanEquals: 0
        Next: OrderRejected
    Default: StandardProcessing

  HighValueApproval:
    Type: Task
    TimeoutSeconds: 3600
    HeartbeatSeconds: 300
    Retry:
      - ErrorEquals: ["States.Timeout"]
        MaxAttempts: 2
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: OrderRejected
        ResultPath: "$.approvalError"
    Next: WaitForConfirmation

  WaitForConfirmation:
    Type: Wait
    Seconds: 10
    Next: StandardProcessing

  StandardProcessing:
    Type: Parallel
    Branches:
      - StartAt: ProcessPayment
        States:
          ProcessPayment:
            Type: Task
            Retry:
              - ErrorEquals: ["PaymentError"]
                MaxAttempts: 3
                BackoffRate: 2.0
            End: true
      - StartAt: ReserveInventory
        States:
          ReserveInventory:
            Type: Task
            End: true
      - StartAt: SendConfirmation
        States:
          SendConfirmation:
            Type: Task
            End: true
    ResultPath: "$.processingResults"
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: OrderRejected
        ResultPath: "$.processingError"
    Next: ProcessLineItems

  ProcessLineItems:
    Type: Map
    ItemsPath: "$.validated.items"
    MaxConcurrency: 5
    ItemProcessor:
      StartAt: FulfillItem
      States:
        FulfillItem:
          Type: Task
          Next: VerifyFulfillment
        VerifyFulfillment:
          Type: Task
          End: true
    ResultPath: "$.fulfillmentResults"
    Next: FinalizeOrder

  FinalizeOrder:
    Type: Task
    Next: OrderComplete

  OrderComplete:
    Type: Succeed

  OrderRejected:
    Type: Fail
    Error: "OrderRejected"
    Cause: "The order could not be processed"
```
