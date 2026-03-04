# IAM policy split for Lambda Durable Functions — hybrid approach
#
# Approach decision (Phase 57, 2026-03-04):
#   Verified AWSLambdaBasicDurableExecutionRolePolicy is available in us-east-2 (v3).
#   All IAM attachment is handled inline on the module block in main.tf using:
#     - attach_policies + number_of_policies + policies (managed policy)
#     - attach_policy_json + policy_json (inline supplement)
#
# Why two policies instead of one all-inline policy:
#
#   MANAGED POLICY (AWSLambdaBasicDurableExecutionRolePolicy v3)
#   AWS-maintained, versioned, forward-compatible with future durable API additions.
#   Covers:
#     - lambda:CheckpointDurableExecution  (checkpoint write during execution replay)
#     - lambda:GetDurableExecutionState    (replay-state read — internal to durable runtime)
#     - logs:CreateLogGroup
#     - logs:CreateLogStream
#     - logs:PutLogEvents
#
#   INLINE SUPPLEMENT (Sid: DurableExtraPermissions in main.tf policy_json)
#   Actions present in RSF's existing iam.tf.j2 generator but NOT in the managed policy.
#   Required for RSF's orchestration model:
#     - lambda:InvokeFunction              (self-invoke — RSF checkpoint/resume pattern)
#     - lambda:ListDurableExecutionsByFunction  (RSF durable runtime enumeration)
#     - lambda:GetDurableExecution         (describe API — user-facing, distinct from GetDurableExecutionState)
#
# Both GetDurableExecution and GetDurableExecutionState are included:
#   GetDurableExecutionState = replay-state API (managed policy, internal to durable runtime)
#   GetDurableExecution      = describe API (inline supplement, user-facing)
#   See SCHEMA-FINDINGS.md Section 3 for full action name mapping table.
#
# If AWSLambdaBasicDurableExecutionRolePolicy becomes unavailable in a target region,
# fall back to all-inline with all 5 actions plus CW Logs.
