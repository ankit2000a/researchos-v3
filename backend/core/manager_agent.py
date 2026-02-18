import uuid
import logging
import asyncio
from typing import Dict, Any
from core.vision_specialist import VisionSpecialist
from core.data_architect import DataArchitect
from core.auditor import Auditor
from core.compliance import ComplianceLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManagerAgent:
    """
    Orchestrator for the ResearchOS V3 Pipeline.
    """
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.specialist = VisionSpecialist() # Renamed from self.vision
        self.architect = DataArchitect()
        self.auditor = Auditor(self.session_id) # Fix: Pass session_id
        self.compliance = ComplianceLogger(self.session_id)
        logger.info(f"ManagerAgent initialized. Session ID: {self.session_id}")

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Main processing pipeline for Truth Engine"""
        
        logger.info("📋 Starting ResearchOS Truth Engine...")
        
        try:
            # Step 1: Vision Processing
            logger.info("Step 1: Vision Processing...")
            narrative, vision_map = self.specialist.process_pdf(file_path) # Used self.specialist
            
            logger.info(f"✅ Vision complete - Extracted {len(narrative)} chars, {len(vision_map)} data points")
            
            # Step 2: Data Extraction (CRITICAL: Pass both arguments)
            # Step 2: Data Architect extracts fields
            # Fix: Use extract_fields instead of extract_data
            logger.info("Step 2: Data Extraction...")
            extracted_data = self.architect.extract_fields(narrative, vision_map) # Corrected variable name and arguments
            
            logger.info(f"✅ Data extraction complete - {len(extracted_data)} fields extracted")
            
            # Step 3: Verification (Truth Engine)
            logger.info("Step 3: Verification (Truth Engine)...")
            verified_data = self.auditor.audit_extraction(extracted_data, narrative, vision_map)
            
            logger.info(f"✅ Verification complete")
            
            # Step 4: Compliance Audit Trail
            audit_trail = self.compliance.get_audit_trail()
            
            return {
                "session_id": self.session_id,
                "status": "COMPLETED",
                "verified_data": verified_data, # Changed from final_report
                "vision_map": vision_map,
                "narrative": narrative[:500], # Changed from markdown_text
                "audit_trail": audit_trail
            }
            
        except Exception as e:
            logger.error(f"❌ Processing pipeline failed: {e}")
            raise
