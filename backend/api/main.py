from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import logging
import os
import json
import shutil
import uuid
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

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
# Global Manager Instance (Mock Session)
manager = ManagerAgent()
latest_result = {}

# Mount uploads directory for frontend access
upload_dir = Path("uploads")
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# In-memory session store for uploaded files
session_files = {}

class AuditRequest(BaseModel):
    file_path: str

@app.get("/")
def read_root():
    return {"status": "ResearchOS V3 Backend Online"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF for processing"""
    
    # Save uploaded file
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Store file path with session
    session_files[session_id] = file_path
    
    return {
        "session_id": session_id,
        "filename": file.filename,
        "message": "File uploaded successfully"
    }

@app.get("/process/{session_id}")
async def process_pdf(session_id: str):
    """Process an uploaded PDF"""
    global latest_result
    
    if session_id not in session_files:
        raise HTTPException(status_code=404, detail="Session not found")
    
    file_path = session_files[session_id]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        logging.info(f"Processing session {session_id} with file {file_path}")
        result = manager.process_document(file_path)
        result["session_id"] = session_id
        latest_result = result
        return result
    except Exception as e:
        logging.error(f"❌ Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/audit")
async def start_audit(request: AuditRequest, background_tasks: BackgroundTasks):
    """
    Legacy/Manual audit endpoint.
    """
    global latest_result
    try:
        # Run synchronously for V3 scaffold simplicity (or async wrapper)
        # Using the mock PDF filename if none provided
        target_file = request.file_path if request.file_path else "conflict_study.pdf"
        
        result = manager.process_document(target_file)
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
