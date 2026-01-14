import pytest
import os
import json
from core.auditor import Auditor
from core.compliance import VerificationStatus

@pytest.fixture
def auditor():
    return Auditor(session_id="test_session")

def test_auditor_geometric_fail(auditor):
    data = {"p_value": {"value": 0.04, "extracted_value": 0.04}}
    vision_map = [] # Empty vision
    markdown = "Results: P=0.04"
    
    result = auditor.audit_extraction(data, markdown, vision_map)
    
    item = result["p_value"]
    assert item["verification_status"] == VerificationStatus.GEOMETRIC_FAIL
    assert item["confidence_score"] == 0.0

def test_auditor_critical_conflict(auditor):
    data = {"p_value": {"value": 0.04, "extracted_value": 0.04}}
    vision_map = [{"text": "0.04", "bbox": [10, 10, 10, 10], "conf": 0.9}]
    markdown = "The result was not statistically significant." # Contradiction
    
    result = auditor.audit_extraction(data, markdown, vision_map)
    
    item = result["p_value"]
    assert item["verification_status"] == VerificationStatus.CRITICAL_CONFLICT
    assert item["confidence_score"] == 0.45
