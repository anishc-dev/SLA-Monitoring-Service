import logging
import json


def info(*args, **kwargs):
    logging.info(*args, **kwargs)
    print(f"INFO: {json.dumps(args)} {json.dumps(kwargs)}")

def error(*args, **kwargs):
    logging.error(*args, **kwargs)
    print(f"ERROR: {args} {kwargs}")