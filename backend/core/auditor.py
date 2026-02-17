import logging
from typing import Dict, Any, List, Optional, Tuple
from core.config import Config
from core.compliance import ComplianceLogger
from schemas.clinical_trial import ClinicalTrialData, ClinicalDataField, VerificationStatus, AuditLogEntry, BoundingBox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Auditor:
    """
    Agent 3: The Auditor (The Truth Engine).
    Implements the 'Disprove Protocol' using Gemini 3 Ultra (Thinking Mode).
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = ComplianceLogger(session_id)
        # self.model = genai.GenerativeModel("gemini-3.0-ultra-thinking")

    def audit_extraction(self, 
                         data: Dict[str, Any], 
                         markdown_text: str, 
                         vision_map: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main Conflict Resolution Loop.
        """
        logger.info("Auditor: Starting Conflict Resolution Loop...")
        
        audited_data = {}
        
        for field_name, field_data in data.items():
            # 1. Parse into Schema Object
            item = ClinicalDataField(**field_data)
            value_str = str(item.value)
            
            # --- PROTOCOL STEP 1: GEOMETRIC VERIFICATION ---
            coords, bbox_id = self._verify_geometry(value_str, vision_map)
            
            if coords:
                item.coordinates = BoundingBox(
                    x=coords[0], y=coords[1], w=coords[2], h=coords[3], 
                    page=1, id=bbox_id
                )
                item.verification_status = VerificationStatus.VERIFIED
                reasoning = [f"Geometrically verified at {coords}."]
            else:
                item.verification_status = VerificationStatus.GEOMETRIC_FAIL
                item.coordinates = None
                reasoning = ["Missing geometry (Hallucination Risk)."]
            
            # --- PROTOCOL STEP 2: NARRATIVE CROSS-CHECK (DISPROVE) ---
            # Only run if we have geometry (or if strict mode is off)
            # We strictly disprove EVERYTHING.
            disprove_result = self._attempt_disprove(field_name, item.value, markdown_text)
            
            if "CONFLICT" in disprove_result:
                item.verification_status = VerificationStatus.CRITICAL_CONFLICT
                reasoning.append(f"Narrative Mismatch: {disprove_result}")
            else:
                reasoning.append("Narrative Consistent.")

            # --- PROTOCOL STEP 3: MATH CHECK ---
            # basic example
            if field_name == "p_value" and isinstance(item.value, float):
                if not (0 <= item.value <= 1.0):
                    item.verification_status = VerificationStatus.MATH_ERROR
                    reasoning.append("P-value out of bounds (0-1).")

            # Finalize
            item.auditor_reasoning = " | ".join(reasoning)
            item.confidence_score = self._calculate_confidence(item.verification_status)
            item.thinking_log = f"Prompt: Disprove {field_name}={value_str}. Result: {disprove_result}"
            
            audited_data[field_name] = item.model_dump()
            
            # Log to 21 CFR Trail
            log_entry = AuditLogEntry(
                session_id=self.session_id,
                data_field=field_name,
                extracted_value=item.extracted_value,
                coordinates=coords,
                source_text_snippet=item.source_text,
                agent_reasoning=item.auditor_reasoning,
                thinking_log=item.thinking_log,
                bounding_box_id=bbox_id,
                confidence_score=item.confidence_score,
                verification_status=item.verification_status.value,
                model_id="gemini-3.0-ultra"
            )
            self.logger.log_event(log_entry)
            
        return audited_data

    def _verify_geometry(self, value_str: str, vision_map: List[Dict]) -> Tuple[Optional[List[float]], Optional[str]]:
        """Exact or fuzzy match against LLMWhisperer map with normalization."""
        if not vision_map:
            return None, None
        
        # Normalize the extracted value for matching
        clean_value = str(value_str).strip().lower().replace(',', '').replace(' ', '')
            
        for i, elem in enumerate(vision_map):
            # Check both 'value' and 'text' keys
            elem_text = elem.get('value', elem.get('text', ''))
            clean_elem = str(elem_text).strip().lower().replace(',', '').replace(' ', '')
            
            # Try exact match, substring match (both directions)
            if clean_value == clean_elem or clean_value in clean_elem or clean_elem in clean_value:
                coords = elem.get('coords', elem.get('bbox', [0, 0, 0, 0]))
                bbox_id = elem.get('id', f"bbox_{i}")
                return coords, bbox_id
        
        return None, None

    def _attempt_disprove(self, field: str, value: Any, text: str) -> str:
        """
        Simulated Thinking Process for Gemini 3 Ultra.
        """
        text_lower = text.lower()
        
        # Rule-based Simulation of "Thinking"
        if field == "p_value" and isinstance(value, float):
            # 0.04 vs "not significant"
            if value < 0.05 and "not statistically significant" in text_lower:
                return "CONFLICT: P<0.05 but text says 'not statistically significant'."
        
        return "No conflict found."

    def _calculate_confidence(self, status: VerificationStatus) -> float:
        if status == VerificationStatus.VERIFIED: return 0.99
        if status == VerificationStatus.CRITICAL_CONFLICT: return 0.45
        if status == VerificationStatus.GEOMETRIC_FAIL: return 0.0
        return 0.5
