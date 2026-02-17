from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
import os
import json
import shutil
import uuid

from core.manager_agent import ManagerAgent
from core.config import Config

# Initialize App
app = FastAPI(title="ResearchOS V3 Truth Engine API")

# Create upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

# Store results by session
sessions = {}

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

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and process it through the Truth Engine pipeline.
    Returns the session_id and processing results.
    """
    try:
        # Save uploaded file
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logging.info(f"Uploaded file saved to: {filepath}")
        
        # Process through pipeline
        manager_instance = ManagerAgent()
        result = manager_instance.process_document(filepath)
        
        # Store results by session
        session_id = manager_instance.session_id
        sessions[session_id] = {
            **result,
            "filename": filename,
            "filepath": filepath
        }
        
        # Also update global for backward compatibility
        global latest_result
        latest_result = result
        
        return {
            "session_id": session_id,
            "status": "COMPLETED",
            "verified_data": result["verified_data"],
            "vision_map": result["vision_map"],
            "narrative": result.get("narrative", ""),
            "audit_trail": result.get("audit_trail", []),
            "filename": filename
        }
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process/{session_id}")
async def get_results_by_session(session_id: str):
    """
    Get processing results for a specific session.
    """
    if session_id in sessions:
        return sessions[session_id]
    raise HTTPException(status_code=404, detail="Session not found")

# Mount uploads directory to serve uploaded PDFs
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
