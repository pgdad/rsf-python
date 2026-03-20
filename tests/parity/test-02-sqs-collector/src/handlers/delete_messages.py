"""Wrapper — imports real handler from handlers.sqs_collector.rsf_handlers."""

from handlers.sqs_collector.rsf_handlers import delete_messages_handler  # noqa: F401 — @state registration
