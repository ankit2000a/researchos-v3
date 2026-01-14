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
        """
        # 1. Vision
        logger.info("Step 1: Vision Processing...")
        markdown_text, vision_map = self.vision.process_pdf(file_path)
        
        # 2. Architect
        logger.info("Step 2: Data Extraction...")
        raw_data = self.architect.extract_data(markdown_text)
        
        # 3. Auditor
        logger.info("Step 3: Verification (Truth Engine)...")
        final_report = self.auditor.audit_extraction(raw_data, markdown_text, vision_map)
        
        return {
            "session_id": self.session_id,
            "status": "COMPLETED",
            "report": final_report,
            "markdown": markdown_text
        }
