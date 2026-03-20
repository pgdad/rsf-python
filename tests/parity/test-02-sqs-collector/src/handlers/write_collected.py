"""Wrapper — imports real handler from handlers.sqs_collector.rsf_handlers."""

from handlers.sqs_collector.rsf_handlers import write_collected_handler  # noqa: F401 — @state registration
