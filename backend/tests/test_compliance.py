import pytest
import json
from core.compliance import ComplianceLogger
from schemas.clinical_trial import AuditLogEntry, VerificationStatus

def test_compliance_hash_chain(tmp_path):
    # Use temp dir for logs
    log_dir = tmp_path / "logs"
    logger = ComplianceLogger(session_id="test_chain", log_dir=str(log_dir))
    
    entry1 = AuditLogEntry(
        session_id="test_chain",
        data_field="field1",
        extracted_value=1.0,
        agent_reasoning="reason",
        confidence_score=1.0,
        verification_status="VERIFIED",
        model_id="test"
    )
    
    entry2 = AuditLogEntry(
        session_id="test_chain",
        data_field="field2",
        extracted_value=2.0,
        agent_reasoning="reason",
        confidence_score=1.0,
        verification_status="VERIFIED",
        model_id="test"
    )
    
    logger.log_event(entry1)
    logger.log_event(entry2)
    
    # Verify file
    log_file = log_dir / "audit_trail_test_chain.json"
    with open(log_file, "r") as f:
        logs = json.load(f)
    
    assert len(logs) == 2
    assert logs[0]["previous_hash"] == "GENESIS_HASH"
    assert logs[1]["previous_hash"] == logs[0]["entry_hash"] # Chain verified
