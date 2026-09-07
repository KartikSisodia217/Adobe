import sys
import json
import logging
from datetime import datetime, timezone

class JSONStderrHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(sys.stderr)

    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, "audit_id"): log_obj["audit_id"] = record.audit_id
        if hasattr(record, "phase"): log_obj["phase"] = record.phase
        if hasattr(record, "url"): log_obj["url"] = record.url
        if hasattr(record, "error_type"): log_obj["error_type"] = record.error_type
        if hasattr(record, "budget_consumption"): log_obj["budget_consumption"] = record.budget_consumption
        
        return json.dumps(log_obj)

logger = logging.getLogger("aimless")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    logger.addHandler(JSONStderrHandler())
