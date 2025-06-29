import logging
import json
import time
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Optional

correlation_id = ContextVar("correlation_id", default="")
ticket_id = ContextVar("ticket_id", default="")
operation = ContextVar('operation', default="")
start_time: ContextVar[Optional[float]] = ContextVar("start_time", default=None)

def set_correlation_id(value):
    correlation_id.set(value)

def set_ticket_id(value):
    ticket_id.set(value)

def set_operation(value):
    operation.set(value)

def start_timer():
    start_time.set(time.time())

def get_latency():
    current_start_time = start_time.get()
    if current_start_time is None:
        return None
    return round((time.time() - current_start_time) * 1000, 2)

def create_log_entry(level: str, message: str, **kwargs):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **kwargs
    }
    if correlation_id.get():
        log_entry["correlation_id"] = correlation_id.get()
    if ticket_id.get():
        log_entry["ticket_id"] = ticket_id.get()
    if operation.get():
        log_entry["operation"] = operation.get()
    
    latency = get_latency()
    if latency is not None:
        log_entry["latency_ms"] = latency
    
    return log_entry

def log(level: str, message: str, **kwargs):
    log_entry = create_log_entry(level, message, **kwargs)
    log_entry_str = json.dumps(log_entry)
    print(log_entry_str)
    logging.info(log_entry_str)

def info(message: str, **kwargs):
    log("info", message, **kwargs)

def error(message: str, **kwargs):
    log("error", message, **kwargs)