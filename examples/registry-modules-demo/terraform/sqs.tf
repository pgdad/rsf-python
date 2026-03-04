# RSF Feature: Dead-letter queue (DLQ) for failed Lambda invocations
# Registry module: terraform-aws-modules/sqs/aws v5.2.1
#
# Conditionally created: count = var.dlq_enabled ? 1 : 0
# When dlq_enabled = false (default), no SQS resources are created.
# When dlq_enabled = true, a SQS queue is created and wired to the Lambda function
# via dead_letter_target_arn in main.tf.
#
# 14-day message retention (1209600 seconds) matches RSF's dlq.tf.j2 template.
# Queue name falls back to "${workflow_name}-dlq" when dlq_queue_name is null.
#
# RSF WorkflowMetadata fields: dlq_enabled, dlq_queue_name, dlq_max_receive_count

module "sqs_dlq" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "5.2.1"
  count   = var.dlq_enabled ? 1 : 0

  name = var.dlq_queue_name != null ? var.dlq_queue_name : "${var.workflow_name}-dlq"

  # 14-day retention — messages remain inspectable for investigation after
  # a Lambda function failure exhausts dlq_max_receive_count retries.
  message_retention_seconds = 1209600

  tags = {
    ManagedBy = "rsf"
    Workflow  = var.workflow_name
  }
}
