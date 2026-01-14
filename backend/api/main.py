from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
import os
import json

from core.manager_agent import ManagerAgent
from core.config import Config

# Initialize App
app = FastAPI(title="ResearchOS V3 Truth Engine API")

# CORS
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Manager Instance (Mock Session)
manager = ManagerAgent()
latest_result = {}

class AuditRequest(BaseModel):
    file_path: str

@app.get("/")
def read_root():
    return {"status": "ResearchOS V3 Backend Online"}

@app.post("/api/audit")
async def start_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    """
    Starts the audit process. 
    In a real app, this would handle file upload. 
    Here we accept a file path (or use default mock).
    """
    global latest_result
    try:
        # Run synchronously for V3 scaffold simplicity (or async wrapper)
        # Using the mock PDF filename if none provided
        target_file = request.file_path if request.file_path else "conflict_study.pdf"
        
        result = manager.run_pipeline(target_file)
        latest_result = result
        return {"status": "COMPLETED", "session_id": result["session_id"]}
    except Exception as e:
        logging.error(f"Audit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/results")
def get_results():
    if not latest_result:
        return {"status": "NO_DATA"}
    return latest_result

@app.get("/api/logs")
def get_logs():
    """Returns the latest session logs."""
    if not latest_result:
        return []
    
    session_id = latest_result.get("session_id")
    log_file = f"{Config.LOG_DIR}/audit_trail_{session_id}.json"
    
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            return json.load(f)
    return []
