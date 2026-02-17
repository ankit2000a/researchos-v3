import uuid
import logging
from typing import Dict, Any
from core.vision_specialist import VisionSpecialist
from core.data_architect import DataArchitect
from core.auditor import Auditor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManagerAgent:
    """
    Orchestrator for the ResearchOS V3 Pipeline.
    """
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.vision = VisionSpecialist()
        self.architect = DataArchitect()
        self.auditor = Auditor(self.session_id)
        logger.info(f"ManagerAgent initialized. Session ID: {self.session_id}")

    def run_pipeline(self, file_path: str) -> Dict[str, Any]:
        """
        Executes the Truth Engine Pipeline.
        Legacy method for backward compatibility.
        """
        return self.process_document(file_path)
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Executes the Truth Engine Pipeline with full vision map support.
        """
        # 1. Vision
        logger.info("Step 1: Vision Processing...")
        narrative, vision_map = self.vision.process_pdf(file_path)
        
        # 2. Architect - pass BOTH narrative and vision_map
        logger.info("Step 2: Data Extraction...")
        raw_data = self.architect.extract_fields(narrative, vision_map)
        
        # 3. Auditor
        logger.info("Step 3: Verification (Truth Engine)...")
        verified_data = self.auditor.audit_extraction(raw_data, narrative, vision_map)
        
        return {
            "session_id": self.session_id,
            "status": "COMPLETED",
            "verified_data": verified_data,
            "report": verified_data,  # backward compatibility
            "narrative": narrative[:500],
            "vision_map": vision_map,
            "audit_trail": []
        }
