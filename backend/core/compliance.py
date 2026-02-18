import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any
import json
import logging
import datetime
import hashlib
from pathlib import Path
from typing import List, Optional
from schemas.clinical_trial import AuditLogEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceLogger:
    """
    Handles 21 CFR Part 11 compliant logging with HASH CHAINING.
    """
    def __init__(self, session_id: str, log_dir: str = "backend/logs"):
        self.session_id = session_id
        if os.path.isabs(log_dir):
            self.log_dir = Path(log_dir)
        else:
             # Make it relative to the backend root if running from there
            self.log_dir = Path(os.getcwd()) / log_dir
            
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"audit_trail_{session_id}.json"
        
        # Initialize if not exists
        if not self.log_file.exists():
            with open(self.log_file, "w") as f:
                json.dump([], f)

    def _calculate_hash(self, data: dict, prev_hash: str) -> str:
        """SHA-256 Hash of (Data + Previous Hash) for immutability."""
        payload = json.dumps(data, sort_keys=True) + prev_hash
        return hashlib.sha256(payload.encode()).hexdigest()

    def log_event(self, entry: AuditLogEntry):
        """
        Logs an event with a cryptographic hash link to the previous entry.
        """
        try:
            # 1. Read existing logs to get the last hash
            with open(self.log_file, "r") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            
            # 2. Get previous hash (GENESIS if empty)
            if logs:
                last_entry = logs[-1]
                prev_hash = last_entry.get("entry_hash", "GENESIS_HASH")
            else:
                prev_hash = "GENESIS_HASH"
            
            # 3. Update entry with chain info
            entry.previous_hash = prev_hash
            
            # 4. Calculate new hash
            entry_dict = entry.model_dump(mode='json')
            # Remove fields that shouldn't be part of the payload if needed, 
            # but usually we hash everything except the hash itself.
            payload_dict = {k: v for k, v in entry_dict.items() if k != "entry_hash"}
            new_hash = self._calculate_hash(payload_dict, prev_hash)
            
            entry.entry_hash = new_hash
            
            # 5. Append and Save
            logs.append(entry.model_dump(mode='json'))
            
            with open(self.log_file, "w") as f:
                json.dump(logs, f, indent=2)
                
            logger.info(f"Compliance Log: {entry.data_field} - {entry.verification_status} [Hash: {new_hash[:8]}...]")
            
        except Exception as e:
            logger.error(f"CRITICAL: Failed to write compliance log: {e}")
            raise

    def get_audit_trail(self) -> List[dict]:
        """Returns the full audit trail for this session."""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []
