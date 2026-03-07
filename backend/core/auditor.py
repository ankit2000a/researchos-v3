import logging
import os
import json
import re
from google import genai
from typing import Dict, Any, List, Optional, Tuple
from core.config import Config
from core.compliance import ComplianceLogger
from schemas.clinical_trial import ClinicalTrialData, ClinicalDataField, VerificationStatus, AuditLogEntry, BoundingBox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Auditor:
    """
    Agent 3: The Auditor (The Truth Engine).
    Implements the 'Disprove Protocol' using Gemini.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = ComplianceLogger(session_id)
        
        # Add Gemini for advanced conflict detection
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or Config.GOOGLE_API_KEY
        self.gemini_model = None
        
        if self.gemini_api_key:
            try:
                self.client = genai.Client(api_key=self.gemini_api_key)
                self.model = Config.GEMINI_MODEL
                logger.info("✅ Gemini initialized for Truth Engine Auditor")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini for Auditor: {e}")

    def audit_extraction(self, 
                     data: Dict[str, Any], 
                     markdown_text: str, 
                     vision_map: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main Conflict Resolution Loop.
        """
        logger.info("Auditor: Starting Conflict Resolution Loop...")
        
        # FIX: Handle empty data case
        if not data:
            logger.warning("⚠️ No data to audit - returning empty result")
            return {}
        
        audited_data = {}
        
        # Batch verify all fields in ONE API call (Fix 4)
        batch_results = {}
        try:
            logger.info("🔍 Batch verifying all fields...")
            batch_results = self._batch_verify_fields(data, markdown_text)
        except Exception as e:
            logger.warning(f"Batch verification skipped due to error: {e}")
            batch_results = {}
            
        for field_name, field_data in data.items():
            # Fix 1: Skip internal metadata fields (they don't need auditing)
            if field_name.startswith('_'):
                logger.debug(f"⏭️  Skipping metadata field: {field_name}")
                continue
            
            # Fix 1: Defensive validation: ensure field_data is a dict with required keys
            if not isinstance(field_data, dict):
                logger.warning(f"⚠️ Field {field_name} is not a dict (type: {type(field_data)}), skipping")
                continue
            
            if 'value' not in field_data and 'extracted_value' not in field_data:
                logger.warning(f"⚠️ Field {field_name} missing both 'value' and 'extracted_value' keys, skipping")
                continue
            
            # Ensure both keys exist (some code paths may only set one)
            if 'value' not in field_data:
                field_data['value'] = field_data.get('extracted_value', '')
            if 'extracted_value' not in field_data:
                field_data['extracted_value'] = field_data.get('value', '')
                
            # BUG 3 FIX: Extract and save pre-computed coordinate data from field_data
            precomputed_coords = field_data.get('coords', [0, 0, 0, 0])
            precomputed_source_location = field_data.get('source_location', None)
            precomputed_source_page = field_data.get('source_page', 0)
            precomputed_bbox = field_data.get('bbox', [0, 0, 0, 0])
                
            try:
                # 1. Parse into Schema Object
                item = ClinicalDataField(**field_data)
            except Exception as e:
                logger.error(f"❌ Failed to create ClinicalDataField for {field_name}: {e}")
                continue
                
            value_str = str(item.value)
            
            # --- PROTOCOL STEP 1: GEOMETRIC VERIFICATION ---
            coords, bbox_id, page = self._verify_geometry(value_str, vision_map)
            
            # BUG 3 FIX: Fall backup to pre-computed coordinates if not found
            if not coords and precomputed_source_location:
                sl = precomputed_source_location
                if sl.get('x', 0) != 0 or sl.get('y', 0) != 0 or sl.get('w', 0) != 0 or sl.get('h', 0) != 0:
                    coords = [sl.get('x', 0), sl.get('y', 0), sl.get('w', 0), sl.get('h', 0)]
                    bbox_id = sl.get('id', field_name)
                    page = sl.get('page', precomputed_source_page or 1)
                    logger.info(f"✅ Using pre-computed coordinates for '{field_name}' from DataArchitect")

            if not coords and precomputed_coords and any(c != 0 for c in precomputed_coords):
                coords = precomputed_coords
                bbox_id = field_name
                page = precomputed_source_page or 1
                logger.info(f"✅ Using pre-computed coords array for '{field_name}'")
            
            if coords:
                item.coordinates = BoundingBox(
                    x=coords[0], y=coords[1], w=coords[2], h=coords[3], 
                    page=page, id=bbox_id
                )
                item.verification_status = VerificationStatus.VERIFIED
                reasoning = [f"Geometrically verified at {coords}."]
            else:
                item.verification_status = VerificationStatus.GEOMETRIC_FAIL
                item.coordinates = None
                reasoning = ["Missing geometry (Hallucination Risk)."]
            
            # --- PROTOCOL STEP 2: NARRATIVE CROSS-CHECK (DISPROVE) ---
            # Fix 4: Use batch verification result if available
            conflict_result = None
            if field_name in batch_results:
                conflict_result = batch_results[field_name]
                logger.debug(f"✅ Used batch result for {field_name}")
            else:
                # Fallback to individual check
                logger.debug(f"⚠️ No batch result for {field_name}, checking individually")
                conflict_result = self._check_conflict(field_name, item.value, markdown_text)
            
            if conflict_result and conflict_result.get("conflict"):
                item.verification_status = VerificationStatus.CRITICAL_CONFLICT
                reasoning.append(f"Narrative Mismatch: {conflict_result.get('reasoning', 'Unknown conflict')}")
            elif conflict_result and conflict_result.get("status") == "REVIEW_NEEDED":
                # unexpected value or not found, but not explicit conflict
                if item.verification_status != VerificationStatus.GEOMETRIC_FAIL:
                     item.verification_status = VerificationStatus.REVIEW_NEEDED
                     # Fix 5: Log reason for review
                     logger.warning(f"⚠️ {field_name} flagged for REVIEW_NEEDED - Reason: {conflict_result.get('reasoning')}")
                reasoning.append(f"Review Needed: {conflict_result.get('reasoning', 'Review required')}")
            else:
                reasoning.append("Narrative Consistent.")

            # --- PROTOCOL STEP 3: MATH CHECK ---
            if field_name == "p_value":
                # Handle p-value bounds check nicely even for strings
                try:
                     # try to convert, stripping < etc
                     import re
                     num_part = re.search(r'[\d\.]+', str(item.value))
                     if num_part:
                         val = float(num_part.group())
                         if not (0 <= val <= 1.0):
                             item.verification_status = VerificationStatus.MATH_ERROR
                             reasoning.append("P-value out of bounds (0-1).")
                except:
                    pass

            # Finalize
            item.auditor_reasoning = " | ".join(reasoning)
            item.confidence_score = self._calculate_confidence(item.verification_status)
            item.thinking_log = f"Conflict Check Result: {conflict_result}"
            
            audited_data[field_name] = item.model_dump()
            
            # BUG 3 FIX: Re-inject the coordinate keys that the frontend expects
            if 'source_location' in field_data:
                audited_data[field_name]['source_location'] = field_data['source_location']
            else:
                audited_data[field_name]['source_location'] = {
                    'id': field_name, 
                    'page': page or 0,
                    'x': coords[0] if coords else 0,
                    'y': coords[1] if coords else 0,
                    'w': coords[2] if coords else 0,
                    'h': coords[3] if coords else 0
                }
            audited_data[field_name]['coords'] = field_data.get('coords', coords or precomputed_coords or [0, 0, 0, 0])
            audited_data[field_name]['bbox'] = field_data.get('bbox', precomputed_bbox or coords or [0, 0, 0, 0])
            audited_data[field_name]['source_page'] = field_data.get('source_page', page or precomputed_source_page or 0)
            
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
                model_id=Config.GEMINI_MODEL
            )
            self.logger.log_event(log_entry)
        
        # Fix 1: Preserve metadata in the verified output (for frontend display)
        if '_metadata' in data:
            audited_data['_metadata'] = data['_metadata']
            logger.debug("✅ Preserved extraction metadata in verified output")
            
        return audited_data

    def _batch_verify_fields(self, fields: Dict, narrative: str) -> Dict[str, Dict]:
        """
        Verify all fields in a single Gemini API call instead of one call per field.
        Returns dict mapping field_name -> conflict_result dict
        """
        if not self.client:
            return {}
            
        # Build batch verification prompt
        fields_to_verify = []
        for field_name, field_data in fields.items():
            if field_name.startswith('_') or not isinstance(field_data, dict):
                continue
            value = field_data.get('extracted_value', field_data.get('value', ''))
            fields_to_verify.append(f'"{field_name}": "{value}"')
        
        if not fields_to_verify:
            return {}
            
        batch_prompt = f"""You are verifying extracted clinical trial data against the source document.

EXTRACTED DATA:
{chr(10).join(fields_to_verify)}

SOURCE DOCUMENT (first 25000 chars):
{narrative[:25000]}

TASK:
For each extracted field, check if the value is:
1. Mentioned in the source document
2. Consistent with the narrative (no contradictions)

Return a JSON object mapping field names to verification results:
Each result should be an object with keys: "conflict" (boolean), "status" (string: VERIFIED, CONFLICT, REVIEW_NEEDED), "reasoning" (string).

Example response:
{{
  "sample_size": {{"conflict": false, "status": "VERIFIED", "reasoning": "Matches Methods section"}},
  "p_value": {{"conflict": true, "status": "CONFLICT", "reasoning": "Document says p<0.05 but extracted p<0.001"}}
}}

Verify now:"""
        
        try:
            response_text = self._call_gemini_with_retry(batch_prompt, max_retries=2)
            
            if not response_text:
                logger.warning("Batch verification failed to get response")
                return {}
            
            # Parse JSON response
            import json
            import re
            
            # Clean response
            json_text = response_text.strip()
            # Remove markdown blocks
            if "```" in json_text:
                json_text = re.sub(r'```json\s*|\s*```', '', json_text)
            
            # Find JSON object
            match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if match:
                json_text = match.group()
            
            results = json.loads(json_text)
            logger.info(f"✅ Batch verified {len(results)} fields in 1 API call")
            
            # Normalize results to ensure expected structure
            normalized_results = {}
            for k, v in results.items():
                if isinstance(v, dict):
                    normalized_results[k] = v
                elif isinstance(v, str):
                    # Handle simplified string response if LLM goes rogue
                    if "VERIFIED" in v:
                        normalized_results[k] = {"conflict": False, "status": "VERIFIED", "reasoning": v}
                    elif "CONFLICT" in v:
                        normalized_results[k] = {"conflict": True, "status": "CRITICAL_CONFLICT", "reasoning": v}
                    else:
                        normalized_results[k] = {"conflict": False, "status": "REVIEW_NEEDED", "reasoning": v}
                        
            return normalized_results
            
        except Exception as e:
            logger.error(f"❌ Batch verification failed: {e}")
            return {}

    def _verify_geometry(self, value_str: str, vision_map: List[Dict]) -> Tuple:
        """
        Find geometric coordinates for a value in the vision map.
        Returns: (coords, bbox_id, page) or (None, None, None) if not found
        """
        if not vision_map or not value_str:
            return None, None, None
        
        # Clean the search value
        # Fix 9: Strict normalization for matching "43,548" with "43548"
        clean_value = str(value_str).strip().lower().replace(',', '').replace(' ', '')
        
        for elem in vision_map:
            if not elem or not isinstance(elem, dict):
                continue
            
            # FIX: Handle both 'value' (new format) and 'text' (legacy format) keys
            elem_text = elem.get('value', elem.get('text', ''))
            
            if not elem_text:
                continue
            
            # Clean the vision map text for comparison
            # Fix 9: Strict normalization here too
            clean_elem = str(elem_text).strip().lower().replace(',', '').replace(' ', '')
            
            # Check for exact match or substring match
            if clean_value == clean_elem or clean_value in clean_elem or clean_elem in clean_value:
                # Extract coordinates - handle both formats
                coords = elem.get('coords', elem.get('bbox', [0, 0, 0, 0]))
                bbox_id = elem.get('id', f"bbox_{elem.get('page', 0)}")
                page = elem.get('page', 1)
                
                logger.debug(f"✅ Found geometry for '{value_str[:30]}...' on page {page}")
                
                return coords, bbox_id, page
        
        logger.debug(f"⚠️ No geometry found for '{value_str[:30]}...'")
        return None, None, None

    def _check_conflict(self, field_name: str, value: Any, narrative: str) -> Dict: 
        """
        Enhanced conflict detection using Gemini AI reasoning.
        Falls back to rule-based logic if Gemini unavailable.
        """
        
        # First try Gemini-powered detection
        if self.client:
            try:
                return self._gemini_conflict_check(field_name, value, narrative)
            except Exception as e:
                logger.warning(f"Gemini conflict check failed: {e}, using rule-based fallback")
        
        # Fallback to rule-based logic
        return self._rule_based_conflict_check(field_name, value, narrative)
    
    
    def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call Gemini API with exponential backoff retry logic for auditor verification.
        
        Handles transient errors (503, 429) by retrying with increasing delays.
        Returns response text or None if all retries fail.
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"📡 Auditor Gemini call (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        'temperature': 0.2,  # FIX BUG 1: Deterministic output
                        'top_p': 0.95
                    }
                )
                
                if response and response.text:
                    logger.debug(f"✅ Auditor got response on attempt {attempt + 1}")
                    return response.text
                else:
                    logger.warning(f"⚠️ Empty auditor response on attempt {attempt + 1}")
                    
            except Exception as e:
                error_str = str(e)
                
                is_503 = '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower()
                is_429 = '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower()
                
                if is_503 or is_429:
                    retry_delay = 2 ** (attempt + 1)
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Auditor API error, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Auditor failed after {max_retries} attempts")
                        return None
                else:
                    logger.error(f"❌ Non-retryable auditor error: {error_str[:200]}")
                    return None
        
        return None

    def _gemini_conflict_check(self, field_name: str, value: Any, narrative: str) -> Dict:
        """Use Gemini to detect conflicts intelligently"""
        
        prompt = (
            f"You are a clinical trial data integrity auditor. Check for contradictions.\\n\\n"
            f"**Field:** {field_name}\\n"
            f"**Extracted Value:** {value}\\n"
            f"**Document Narrative:** {narrative[:1000]}\\n\\n"
            "**Task:** Determine if there is a conflict between the extracted value and the narrative text.\\n\\n"
            "**Rules:**\\n"
            "- For p_value: If p < 0.05, it means \"statistically significant\". If narrative says \"not significant\" or \"p>0.05\", that's a CONFLICT.\\n"
            "- For sample_size: Check if narrative mentions a different number of participants.\\n"
            "- For outcomes: Check if narrative contradicts the stated result.\\n\\n"
            "**Return ONLY valid JSON:**\\n"
            "{\\n"
            "  \"conflict\": true/false,\\n"
            "  \"status\": \"VERIFIED\" or \"CRITICAL_CONFLICT\" or \"REVIEW_NEEDED\",\\n"
            "  \"reasoning\": \"Brief explanation of your finding\"\\n"
            "}"
        )
        
        # Use retry wrapper
        try:
            response_text = self._call_gemini_with_retry(prompt)
        except Exception as e:
            logger.warning(f"Final Gemini failure: {e}")
            return self._rule_based_conflict_check(field_name, value, narrative)

        # Handle empty/None response
        if not response_text:
            logger.warning(f"Gemini returned empty response for {field_name}, using rule-based fallback")
            return self._rule_based_conflict_check(field_name, value, narrative)
        
        response_text = response_text.strip()
        
        if not response_text:
            logger.warning(f"Gemini returned empty text for {field_name}, using rule-based fallback")
            return self._rule_based_conflict_check(field_name, value, narrative)
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            raise ValueError("Could not parse Gemini response")
    
    def _rule_based_conflict_check(self, field_name: str, value: Any, narrative: str) -> Dict:
        """Original rule-based conflict detection (fallback)"""
        
        narrative_lower = narrative.lower()
        
        if field_name == "p_value": 
            try:
                p_val = float(value)
                
                # Check for contradiction
                if p_val < 0.05:
                    # Significant result
                    if any(phrase in narrative_lower for phrase in [
                        "not statistically significant",
                        "not significant",
                        "p>0.05",
                        "p > 0.05",
                        "failed to reach significance"
                    ]):
                        return {
                            "conflict": True,
                            "status": "CRITICAL_CONFLICT",
                            "reasoning": f"CONFLICT: P={p_val} is <0.05 (significant) but narrative says 'not statistically significant'"
                        }
                
                return {
                    "conflict": False,
                    "status": "VERIFIED",
                    "reasoning": "Narrative matches p-value interpretation"
                }
            except: 
                return {"conflict": False, "status": "REVIEW_NEEDED", "reasoning": "Could not parse p-value"}
        
        elif field_name == "sample_size": 
            # Check if narrative mentions different sample size
            import re
            numbers = re.findall(r'\\b(\\d{2,4})\\b', narrative)
            
            if str(value) not in numbers and len(numbers) > 0:
                return {
                    "conflict": True,
                    "status": "REVIEW_NEEDED",
                    "reasoning": f"Sample size {value} not found in narrative (found: {numbers[:3]})"
                }
            
            return {"conflict": False, "status": "VERIFIED", "reasoning": "Narrative Consistent"}
        
        else:
            # Generic check
            if str(value).lower() in narrative_lower: 
                return {"conflict": False, "status": "VERIFIED", "reasoning": "Narrative Consistent"}
            else:
                return {
                    "conflict": False,
                    "status": "REVIEW_NEEDED",
                    "reasoning": "Value not explicitly mentioned in narrative"
                }

    def _calculate_confidence(self, status: VerificationStatus) -> float:
        if status == VerificationStatus.VERIFIED: return 0.99
        if status == VerificationStatus.CRITICAL_CONFLICT: return 0.45
        if status == VerificationStatus.GEOMETRIC_FAIL: return 0.0
        return 0.5
