import pytest
import os
import json
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ResearchOS V3 Backend Online"}

def test_end_to_end_audit():
    # 1. Trigger Audit (Mock)
    payload = {"file_path": "conflict_study.pdf"}
    response = client.post("/api/audit", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    session_id = data["session_id"]
    
    # 2. Get Results
    res_response = client.get("/api/results")
    assert res_response.status_code == 200
    report = res_response.json()["report"]
    
    # Verify Content
    assert "p_value" in report
    assert report["p_value"]["verification_status"] == "CRITICAL_CONFLICT" # as per mock
    
    # 3. Check Logs (Compliance)
    log_response = client.get("/api/logs")
    assert log_response.status_code == 200
    logs = log_response.json()
    
    assert len(logs) >= 3
    # Verify Hash Chain
    assert logs[0]["previous_hash"] == "GENESIS_HASH"
    assert logs[1]["previous_hash"] == logs[0]["entry_hash"]
