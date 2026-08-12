"""Shared logging configuration. Call setup_logging() once, from each
entrypoint's __main__ block, before doing any other work.
"""

import logging

from opentelemetry import trace

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s%(trace_suffix)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _TraceIDFilter(logging.Filter):
    def filter(self, record):
        span_context = trace.get_current_span().get_span_context()
        if span_context.trace_id:
            record.trace_suffix = f" [trace_id={format(span_context.trace_id, '032x')}]"
        else:
            record.trace_suffix = ""
        return True


def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    for handler in logging.getLogger().handlers:
        handler.addFilter(_TraceIDFilter())
