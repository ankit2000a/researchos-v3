import os
import json
import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from google import genai
from core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataArchitect:
    """
    Agent 2: Data Architect (Gemini-powered)
    Takes raw text + vision map and structures it into clinical trial fields.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key and hasattr(Config, 'GOOGLE_API_KEY'):
            self.api_key = Config.GOOGLE_API_KEY
            
        self.client = None
        # Initialize model from Config nicely
        self.model = getattr(Config, 'GEMINI_MODEL', "gemini-1.5-flash")
        
        if self.api_key:
            # Defensive check for key format if it looks like a Google key
            if isinstance(self.api_key, str) and "AIza" not in self.api_key:
                 logger.warning(f"⚠️ API Key does not look like a standard Google key (len={len(self.api_key)})")
            
            try:
                # Removed genai.configure() - new SDK uses Client(api_key=...)
                
                # Check model before using
                if not self.model:
                    self.model = "gemini-1.5-flash"
                    
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"✅ Gemini initialized for Data Architect (model: {self.model})")
            except Exception as e:
                import traceback
                logger.error(f"❌ Failed to initialize Gemini: {e}")
                logger.error(f"📋 Error type: {type(e).__name__}")
                logger.error(f"📋 Full traceback:")
                logger.error(traceback.format_exc())
                self.client = None
        else:
            logger.warning("⚠️  No Gemini API Key - will use mock extraction")
    
    def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call Gemini API with exponential backoff retry logic.
        
        Handles transient errors (503 Service Unavailable, 429 Rate Limit) 
        by retrying with increasing delays: 2s, 4s, 8s.
        
        Args:
            prompt: The prompt to send to Gemini
            max_retries: Maximum number of retry attempts (default: 3)
        
        Returns:
            Response text from Gemini, or None if all retries fail
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📡 Gemini API call (attempt {attempt + 1}/{max_retries})")
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        'temperature': 0.2,  # FIX BUG 1: Low temperature for deterministic results
                        'top_p': 0.95,
                        'top_k': 40
                    }
                )
                
                # Success - return response text
                if response and response.text:
                    logger.info(f"✅ Gemini responded successfully on attempt {attempt + 1}")
                    return response.text
                else:
                    logger.warning(f"⚠️ Empty response from Gemini on attempt {attempt + 1}")
                    
            except Exception as e:
                error_str = str(e)
                
                # FIX BUG 2: Check if it's a retryable error
                is_503 = '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower()
                is_429 = '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower()
                
                if is_503 or is_429:
                    # Exponential backoff: 2s, 4s, 8s
                    retry_delay = 2 ** (attempt + 1)
                    
                    if attempt < max_retries - 1:
                        # Still have retries left
                        error_type = "503 Service Overloaded" if is_503 else "429 Rate Limit"
                        logger.warning(f"⚠️ Gemini API error: {error_type}")
                        logger.info(f"⏳ Retrying in {retry_delay} seconds (attempt {attempt + 2}/{max_retries})...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Out of retries
                        logger.error(f"❌ Gemini API failed after {max_retries} attempts")
                        logger.error(f"Final error: {error_str[:300]}")
                        return None
                else:
                    # Non-retryable error (e.g., invalid API key, malformed request)
                    logger.error(f"❌ Non-retryable Gemini error: {error_str[:300]}")
                    return None
        
        return None

    def extract_fields(self, narrative: str, vision_map: List[Dict]) -> Dict[str, Any]:
        """
        Extract structured fields from narrative text and vision map. 
        Returns: {field_name: {"value": ..., "coords": [x,y,w,h]}}
        """
        if not self.client:
            logger.warning("DataArchitect: No API client. Using Mock Extraction.")
            return self._mock_extract(vision_map)
        
        logger.info("🏗️  Extracting structured fields with Gemini...")
        logger.info(f"📊 Narrative length: {len(narrative)} chars")
        logger.info(f"📊 Vision map size: {len(vision_map)} points")
        
        # Calculate document coverage percentage
        original_length = len(narrative)
        # Note: prompt creation may truncate narrative


        # Check if truncation happened
        # We need to check the actual length used in prompt or passed to prompt
        # Since _create_extraction_prompt modifies it internally, we can't easily check here unless we duplicate logic 
        # or rely on the log inside _create_extraction_prompt.
        # But the User request specifically asked to add it *after* these lines.
        # Let's trust _create_extraction_prompt logic which I will update next.
        # Actually, to log it *here* as requested, I need to know if it *will* be truncated.
        
        # Re-implementing check here for logging purposes as requested:
        max_narrative_length_limit = 500000
        if len(narrative) > max_narrative_length_limit:
             coverage_pct = (max_narrative_length_limit / original_length) * 100
             logger.warning(f"⚠️ Document truncated: Sending {max_narrative_length_limit} of {original_length} chars ({coverage_pct:.1f}% coverage)")
        else:
             logger.info(f"✅ Sending complete document: {len(narrative)} characters (100% coverage)")

        try:
            # Create prompt for Gemini
            prompt = self._create_extraction_prompt(narrative, vision_map)
            
            logger.info("📡 Calling Gemini API with retry logic...")

            # FIX BUG 2: Call Gemini with automatic retry for 503/429 errors
            response_text = self._call_gemini_with_retry(prompt, max_retries=3)

            # Check if retry logic exhausted all attempts
            if not response_text:
                logger.error("❌ Gemini returned empty response after all retry attempts")
                raise Exception("Gemini API Rate Limit or Overload: Exhausted all retry attempts.")
            
            # Pass directly to response text handler (though we have text now, current flow expects response obj or we bypass)
            # Actually, the original code had: response = self.client... 
            # Then: response_text = self._extract_response_text(response)
            # Since _call_gemini_with_retry returns text, we can skip _extract_response_text or adapt.
            # Let's see... the next line in original code is: response_text = self._extract_response_text(response)
            # We already have response_text. So we should modify the next lines too to avoid error.
            
            # We'll just assign it and skip the next call. 
            # Wait, I need to match the TargetContent exactly.
            # I will include lines 52-66 in TargetContent to handle the transition.
            
            # FIX: Better response extraction - try multiple ways
            # We already have response_text from the retry method
            # response_text = self._extract_response_text(response) # No longer needed
            
            if not response_text:
                logger.error("❌ Could not extract text from Gemini response")
                raise Exception("Gemini extraction failed: Could not extract text from response.")
            
            logger.info(f"✅ Gemini responded with {len(response_text)} characters")
            
            # Safe logging - only log first 500 chars
            preview = response_text[:500] if len(response_text) > 500 else response_text
            logger.info(f"📊 Gemini raw response: {preview}...")
            
            # Parse JSON response
            extracted = self._parse_gemini_response(response_text, vision_map)
            
            # Check if parsing returned empty dict (failed to extract)
            if not extracted:
                logger.error("❌ Failed to parse any fields from Gemini response")
                raise Exception("Gemini extraction failed: Could not parse any fields from JSON response.")
            
            # Link extracted fields to PDF coordinates
            if vision_map:
                extracted = self._link_fields_to_coordinates(extracted, vision_map)
            else:
                logger.warning("No vision map available - fields will not have source locations")
            
            # Verify all required fields present
            expected_fields = ['p_value', 'sample_size', 'primary_endpoint_result']
            missing = [f for f in expected_fields if f not in extracted]
            if missing:
                logger.warning(f"⚠️ Gemini missed fields: {missing}")

            # Handle missing p_value gracefully (some papers use Bayesian credible intervals)
            if 'p_value' not in extracted or not extracted.get('p_value'):
                logger.info("ℹ️ P-value not found in document - may use Bayesian credible intervals, confidence intervals, or other statistics")
                
                # Create a placeholder entry so the field exists in the response
                extracted['p_value'] = {
                    'value': 'Not reported',
                    'extracted_value': 'Not reported',
                    'coords': [0, 0, 0, 0],
                    'source_page': 0,
                    'bbox': [0, 0, 0, 0],
                    'source_location': {
                        'id': 'p_value',
                        'page': 0,
                        'x': 0,
                        'y': 0,
                        'w': 0,
                        'h': 0
                    },
                    'note': 'P-value not explicitly reported in primary endpoint (may use credible/confidence intervals instead)'
                }
                
                logger.info("✅ Added p_value placeholder: 'Not reported'")
            
            logger.info(f"✅ Extracted {len(extracted)} fields with Gemini")
            if extracted:
                logger.info(f"Fields extracted: {list(extracted.keys())}")
            
            # Add extraction metadata for reproducibility
            extracted['_metadata'] = {
                'extraction_timestamp': datetime.utcnow().isoformat() + 'Z',
                'model_version': self.model,
                'temperature': 0.2,
                'narrative_length': len(narrative),
                'narrative_hash': hashlib.sha256(narrative.encode()).hexdigest()[:16],
                'vision_map_points': len(vision_map),
                'fields_extracted_count': len(extracted),
                'extraction_config': {
                    'temperature': 0.2,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_narrative_chars': 25000
                }
            }

            logger.info(f"📋 Extraction metadata: model={self.model}, temp=0.2, fields={len(extracted)}")
            
            return extracted
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
                logger.error("⚠️ Gemini quota exceeded — returning error to frontend")
                raise Exception("Gemini API Rate Limit or Overload: Quota Exhausted.")
            logger.error(f"❌ Gemini extraction failed: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise e

    def _extract_response_text(self, response) -> str:
        """Extract text from Gemini response object - tries multiple methods"""
        
        if response is None:
            logger.error("❌ Gemini returned None response object")
            return None
        
        response_text = None
        
        # Debug: Log what we got
        logger.info(f"📊 Response object type: {type(response)}")
        
        # Method 1: Direct .text attribute
        try:
            if hasattr(response, 'text') and response.text:
                response_text = response.text
                logger.info("✅ Got text via response.text")
                return response_text
        except Exception as e:
            logger.warning(f"Could not access response.text: {e}")
        
        # Method 2: Through candidates
        try:
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"📊 Found {len(response.candidates)} candidates")
                candidate = response.candidates[0]
                
                # Log candidate info
                if hasattr(candidate, 'finish_reason'):
                    logger.info(f"📊 Finish reason: {candidate.finish_reason}")
                
                if hasattr(candidate, 'content') and candidate.content:
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        logger.info(f"📊 Found {len(content.parts)} parts")
                        for i, part in enumerate(content.parts):
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text
                                logger.info(f"✅ Got text via candidates[0].content.parts[{i}].text")
                                return response_text
        except Exception as e:
            logger.warning(f"Could not access via candidates: {e}")
        
        # Method 3: Check for 'parts' directly on response
        try:
            if hasattr(response, 'parts') and response.parts:
                for i, part in enumerate(response.parts):
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
                        logger.info(f"✅ Got text via response.parts[{i}].text")
                        return response_text
        except Exception as e:
            logger.warning(f"Could not access response.parts: {e}")
        
        # Method 4: Try dict-like access
        try:
            if hasattr(response, 'get'):
                text = response.get('text') or response.get('content')
                if text:
                    response_text = str(text)
                    logger.info("✅ Got text via dict-like access")
                    return response_text
        except Exception as e:
            logger.warning(f"Could not access via dict: {e}")
        
        # Method 5: Try to convert to string and look for JSON
        try:
            response_str = str(response)
            if response_str and len(response_str) > 20 and '{' in response_str:
                # Try to find JSON in the string
                json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
                if json_match:
                    response_text = json_match.group()
                    logger.info("✅ Got text via str(response) JSON extraction")
                    return response_text
        except Exception as e:
            logger.warning(f"Could not convert response to string: {e}")
        
        # Debug: Print everything about the response if we failed
        logger.error(f"❌ All extraction methods failed")
        try:
            logger.error(f"Response dir: {dir(response)}")
            logger.error(f"Response repr: {repr(response)[:1000]}")
        except Exception as e:
            logger.error(f"Could not debug response: {e}")
        
        return None

    def _create_extraction_prompt(self, narrative: str, vision_map: List[Dict]) -> str:
        """Create a prompt for Gemini to extract structured clinical trial fields"""
        
        # Guard against None or empty narrative
        if not narrative:
            logger.warning("⚠️ Empty narrative provided to _create_extraction_prompt")
            narrative = "[No document text available]"
        
        # Truncate narrative if too long (Gemini has context limits)
        # Gemini 1.5 Flash supports 1M tokens (~4M characters)
        # Only truncate if document is extremely large (>500K chars = edge case)
        max_narrative_length = 500000

        if len(narrative) > max_narrative_length:
            # Edge case: Document is unusually large (>500K chars)
            narrative = narrative[:max_narrative_length]
            logger.warning(f"⚠️ Document extremely large ({len(narrative)} chars), truncated to {max_narrative_length}")
        else:
            # Normal case: Send full document
            logger.info(f"📄 Sending full narrative to Gemini ({len(narrative)} characters, no truncation)")
        
        # FIX BUG 3: Improved prompt with explicit p-value extraction instructions
        prompt = f"""You are a clinical trial data extraction expert. Extract key fields from this document.
        
⚠️ CRITICAL PRIORITY FIELD ⚠️
Before extracting anything else, find the PRIMARY ENDPOINT P-VALUE first.

DOCUMENT TEXT:
{narrative}

EXTRACTION TASK:

🔴 HIGHEST PRIORITY - MUST EXTRACT:

"p_value" - The PRIMARY ENDPOINT p-value or statistical significance value
   
   ⚠️ CRITICAL: This is the MOST IMPORTANT field to extract
   
   SEARCH STRATEGY (check in this order):
   1. ABSTRACT: Look for "p<0.05", "p<0.001", "statistically significant"
   2. RESULTS SECTION: First paragraph after "Results" heading
   3. RESULTS TABLES: Table 2, Table 3 captions and cells
   4. FIGURE CAPTIONS: "Figure 2: Efficacy analysis (p<0.001)"
   5. STATISTICAL ANALYSIS: Dedicated statistics section
   6. PRIMARY ENDPOINT PARAGRAPH: Search for "primary endpoint" + nearby p-value
   
   FORMATS TO RECOGNIZE:
   - Standard: "p<0.001", "p=0.04", "P=0.0123", "p < 0.05"
   - With text: "statistically significant (p<0.05)"
   - With symbols: "p<0·001" (middle dot), "P≤0.001"
   - Scientific: "p=1.2×10⁻⁵", "p=1.2e-5"
   - Contextual: "achieved significance (P<0.001)"
   
   WHAT TO RETURN:
   - Return as STRING: "<0.001" NOT 0.001 (preserve inequality symbols)
   - Extract ONLY the primary endpoint p-value (ignore secondary endpoints)
   - If multiple p-values exist, choose the one associated with the primary outcome
   
   IF NOT FOUND:
   - Search thoroughly through the ENTIRE document before giving up
   - Some papers use "credible interval" (Bayesian) or "confidence interval" instead
   - If truly absent after thorough search, OMIT the field (do NOT make up a value)
   - DO NOT return null or "N/A" - just omit the field from JSON response

"sample_size" - Total participants enrolled (return as INTEGER without commas)
   Example: "43,548 participants" → return 43548

"primary_endpoint_result" - Main study outcome with full context
   Must include: efficacy %, description, confidence interval
   Example: "95% vaccine efficacy (95% CI: 90.3-97.6) in preventing Covid-19"

🟢 OPTIONAL FIELDS (extract if found):

"study_title" - Full study title
"drug_name" - Drug/intervention name  
"study_duration" - Study length (e.g., "12 weeks", "median of 2 months")
"efficacy_rate" - Efficacy percentage (e.g., "95%")
"adverse_events" - Safety findings (include severity: mild/moderate/severe)
"conclusion" - Main conclusion (complete sentence)

RESPONSE FORMAT - JSON ONLY (no markdown, no code blocks):
{{"p_value": "<0.001", "sample_size": 43548, "primary_endpoint_result": "95% efficacy (95% CI: 90.3-97.6)", "study_title": "...", "drug_name": "...", "study_duration": "...", "efficacy_rate": "95%", "adverse_events": "...", "conclusion": "..."}}

CRITICAL RULES:
1. ALWAYS extract p_value if it exists anywhere in the document
2. If p_value not found after thorough search, omit it (do NOT make one up)
3. Omit fields that cannot be found (no null values)
4. Use exact document wording where possible

Extract now:"""

        return prompt

    def _parse_gemini_response(self, response_text: str, vision_map: List[Dict]) -> Dict[str, Any]:
        """Parse Gemini's JSON response"""
        
        if not response_text:
            logger.error("Empty response text provided to parser")
            return {}
        
        try:
            # Try to find JSON block wrapped in ```json ... ``` or just { ... }
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
            else:
                # If regex fails, try cleaning markdown manually
                json_str = response_text.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:]
                elif json_str.startswith("```"):
                    json_str = json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                json_str = json_str.strip()

            if not json_str:
                raise ValueError("Could not find any JSON-like content")

            logger.info(f"📊 Attempting to parse JSON ({len(json_str)} chars)")
            data = json.loads(json_str)
            
            if not isinstance(data, dict):
                logger.error(f"Parsed JSON is not a dict: {type(data)}")
                return {}
            
            # Match extracted values with specific type handling
            result = {}
            
            for field_name, value in data.items():
                if value is None:
                    continue
                
                # Special handling for p_value (keep as string)
                if field_name == 'p_value':
                    result[field_name] = {
                        "value": str(value),
                        "extracted_value": str(value),
                        "extracted_type": "string",
                        "source_text": str(value)
                    }
                elif field_name == 'sample_size':
                    try:
                        # Handle comma-separated numbers
                        int_val = int(str(value).replace(',', ''))
                        result[field_name] = {
                            "value": int_val,
                            "extracted_value": int_val,
                            "extracted_type": "integer",
                            "source_text": str(value)
                        }
                    except ValueError:
                        result[field_name] = {
                            "value": value,
                            "extracted_value": value,
                            "extracted_type": "string",
                            "source_text": str(value)
                        }
                else:
                    result[field_name] = {
                        "value": value,
                        "extracted_value": value,
                        "extracted_type": "string",
                        "source_text": str(value)
                    }
            
            logger.info(f"✅ Parsed {len(result)} fields from JSON: {list(result.keys())}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Bad JSON string (first 500 chars): {response_text[:500]}...")
            return {}
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _normalize_for_matching(self, text: str) -> str:
        """
        Normalize text for coordinate matching by removing common formatting.
        Handles commas in numbers, smart quotes, dashes, etc.
        """
        if not text:
            return ""
        
        text = str(text)
        
        # Remove common number formatting
        text = text.replace(',', '')  # 43,548 -> 43548
        text = text.replace(' ', '')  # Remove spaces
        
        # Remove common punctuation variations
        text = text.replace('–', '-')  # En dash -> hyphen
        text = text.replace('—', '-')  # Em dash -> hyphen
        text = text.replace("’", "'")  # Smart single quote -> regular single quote
        text = text.replace('“', '"').replace('”', '"') # Smart double quotes -> regular double quote
        text = text.replace('"', '"')  # Regular double quote (noop but keeps logic clear)
        
        # Normalize whitespace (though we removed all spaces above, this is for safety if we change logic)
        text = ' '.join(text.split())
        
        return text.lower()

    def _link_fields_to_coordinates(self, extracted_fields: Dict, vision_map: List[Dict]) -> Dict:
        """
        Find source coordinates for each extracted field by searching vision map.
        Uses a cascade of strategies:
        1. Exact substring match (highest confidence)
        2. Text Normalized Match (ignores punctuation)
        3. Fuzzy match (SequenceMatcher)
        4. Fallback for short values (first occurrence)
        """
        from difflib import SequenceMatcher
        import re
        
        if not vision_map:
            logger.warning("No vision map available for coordinate linking")
            return extracted_fields
        
        logger.info(f"🔗 Linking {len(extracted_fields)} fields to {len(vision_map)} coordinate points")

        for field_name, field_data in extracted_fields.items():
            # Skip metadata
            if field_name.startswith('_'):
                continue
                
            value = str(field_data.get('extracted_value', ''))
            
            # Skip if no value
            if not value or value == 'None' or value == 'Not reported':
                continue

            # Find coordinates using 5-tier strategy
            location = self._find_coordinates_for_value(value, vision_map)

            if location:
                # Add location to field data in preferred format
                field_data['source_location'] = {
                    'id': field_name,
                    'page': location['page'],
                    'x': location['x'],
                    'y': location['y'],
                    'w': location['w'],
                    'h': location['h']
                }
                # Legacy format for backward compatibility
                field_data['coords'] = [
                    location['x'],
                    location['y'],
                    location['w'],
                    location['h']
                ]
                field_data['bbox'] = field_data['coords']
                field_data['source_page'] = location['page']
                
                logger.info(f"✅ Linked '{field_name}' to page {location['page']}")
            else:
                # Default empty coordinates
                field_data['source_location'] = {
                    'id': field_name,
                    'page': 0, 
                    'x': 0, 'y': 0, 'w': 0, 'h': 0
                }
                field_data['coords'] = [0, 0, 0, 0]
                field_data['bbox'] = [0, 0, 0, 0]
                field_data['source_page'] = 0
                logger.warning(f"❌ Could not find coordinates for '{field_name[:20]}...'")
        
        return extracted_fields

    def _find_coordinates_for_value(self, extracted_value: str, vision_map: List[Dict]) -> Dict:
        """
        Find coordinates in vision map for an extracted value.
        Uses 5-tier matching strategy: Exact -> Normalized -> Substring -> Fuzzy -> Fallback
        """
        import re
        from difflib import SequenceMatcher
        
        # Tier 0: Handle None/empty
        if not extracted_value or not vision_map:
            return None
        
        extracted_str = str(extracted_value).strip()
        normalized_extracted = self._normalize_for_matching(extracted_str)
        
        best_match = None
        best_score = 0
        
        for item in vision_map:
            if not item: continue
            
            vision_text = str(item.get('value', item.get('text', ''))).strip()
            if not vision_text: continue
            
            # TIER 1: EXACT MATCH (fastest)
            if extracted_str == vision_text:
                logger.info(f"🎯 Exact match found for '{extracted_str[:30]}...'")
                return self._extract_coords_from_item(item)
            
            # TIER 2: NORMALIZED MATCH (handles formatting)
            normalized_vision = self._normalize_for_matching(vision_text)
            
            if normalized_extracted == normalized_vision:
                logger.info(f"🎯 Normalized match found for '{extracted_str[:30]}...' (matched '{vision_text[:30]}...')")
                return self._extract_coords_from_item(item)
            
            # TIER 3: SUBSTRING MATCH (for longer extractions)
            if len(normalized_extracted) > 10:
                if normalized_extracted in normalized_vision or normalized_vision in normalized_extracted:
                    # Valid substring match for reasonably long string is high confidence
                    score = 0.95 
                    if score > best_score:
                        best_score = score
                        best_match = item
            
            # TIER 4: FUZZY MATCH (handles OCR errors)
            if best_score < 0.9: # Only check fuzzy if we don't have a strong match yet
                similarity = SequenceMatcher(None, normalized_extracted, normalized_vision).ratio()
                if similarity > 0.90 and similarity > best_score:  # 90% threshold for fuzzy
                    best_score = similarity
                    best_match = item
        
        # TIER 3.5: PREFIX MATCH (for multi-line extractions like primary_endpoint_result)
        if not best_match and len(extracted_str) > 30:
            # Check if the first 30 chars exist in any vision block (anchors long multi-line sentences)
            prefix = self._normalize_for_matching(extracted_str[:30])
            for item in vision_map:
                if not item: continue
                vision_text = self._normalize_for_matching(str(item.get('value', item.get('text', ''))))
                if prefix in vision_text or vision_text in prefix:
                    logger.info(f"🎯 Prefix match found for '{extracted_str[:30]}...'")
                    return self._extract_coords_from_item(item)

        # Return best match if found from Tier 3 or 4
        if best_match and best_score > 0.85:
            logger.info(f"🎯 Best match found for '{extracted_str[:30]}...' with score {best_score:.2f}")
            return self._extract_coords_from_item(best_match)
        
        # TIER 5: FALLBACK FOR SHORT VALUES (like "95%")
        # Only if no high confidence match was found
        if len(extracted_str) < 10:
            for item in vision_map:
                vision_text = self._normalize_for_matching(str(item.get('value', item.get('text', ''))))
                if normalized_extracted in vision_text:
                    logger.info(f"🎯 Fallback match found for short value '{extracted_str}'")
                    return self._extract_coords_from_item(item)
        
        return None

    def _extract_coords_from_item(self, item: Dict) -> Dict:
        """Helper to standardize coordinate extraction from vision map item"""
        coords = item.get('coords', item.get('bbox', [0, 0, 0, 0]))
        page = item.get('page', 1)
        
        # Ensure coords format [x, y, w, h] or similar
        # If header/metadata says x,y,w,h in dict, use that
        x, y, w, h = 0, 0, 0, 0
        
        if isinstance(coords, list) and len(coords) >= 4:
            x, y, w, h = coords[0], coords[1], coords[2], coords[3]
        
        return {
            'page': page,
            'x': x,
            'y': y,
            'w': w,
            'h': h
        }
    
    def _mock_extract(self, vision_map: List[Dict]) -> Dict[str, Any]:
        """Mock extraction - returns realistic test data for the Pfizer vaccine paper"""
        
        logger.info("📋 Using mock extraction with synthetic data")
        
        # Return proper mock data that will work with the auditor
        # These values are based on the actual Pfizer BNT162b2 vaccine trial
        result = {
            "p_value": {
                "value": "<0.001",
                "extracted_value": "<0.001",
                "extracted_type": "string",
                "source_text": "p<0.001",
                "coords": [0, 0, 0, 0],
                "bbox": [0, 0, 0, 0],
                "source_page": 1
            },
            "sample_size": {
                "value": 43548,
                "extracted_value": 43548,
                "extracted_type": "integer",
                "source_text": "A total of 43,548 participants",
                "coords": [0, 0, 0, 0],
                "bbox": [0, 0, 0, 0],
                "source_page": 1
            },
            "primary_endpoint_result": {
                "value": "95% efficacy in preventing Covid-19",
                "extracted_value": "95% efficacy in preventing Covid-19",
                "extracted_type": "string",
                "source_text": "BNT162b2 was 95% effective in preventing Covid-19",
                "coords": [0, 0, 0, 0],
                "bbox": [0, 0, 0, 0],
                "source_page": 1
            }
        }
        
        # Try to find actual values from vision_map if available
        if vision_map:
            for item in vision_map:
                if not item:
                    continue
                text = str(item.get('value', item.get('text', '')))
                text_lower = text.lower()
                
                # Look for p-value patterns
                if 'p<' in text_lower or 'p =' in text_lower or 'p=' in text_lower or 'p-value' in text_lower:
                    p_match = re.search(r'p\s*[<=]\s*([\d.]+)', text_lower)
                    if p_match:
                        p_val = f"<{p_match.group(1)}"
                        result['p_value']['value'] = p_val
                        result['p_value']['extracted_value'] = p_val
                        result['p_value']['source_text'] = text
                        coords = item.get('coords', item.get('bbox', [0, 0, 0, 0]))
                        result['p_value']['coords'] = coords
                        result['p_value']['bbox'] = coords
                        result['p_value']['source_page'] = item.get('page', 1)
                        logger.info(f"📋 Mock found p_value: {p_val}")
                
                # Look for sample size patterns  
                if 'participant' in text_lower or 'patient' in text_lower or 'total of' in text_lower:
                    n_match = re.search(r'(\d{1,3}(?:,\d{3})+|\d{4,})', text)
                    if n_match:
                        try:
                            n_val = int(n_match.group(1).replace(',', ''))
                            if n_val > 100:  # Reasonable sample size
                                result['sample_size']['value'] = n_val
                                result['sample_size']['extracted_value'] = n_val
                                result['sample_size']['source_text'] = text
                                coords = item.get('coords', item.get('bbox', [0, 0, 0, 0]))
                                result['sample_size']['coords'] = coords
                                result['sample_size']['bbox'] = coords
                                result['sample_size']['source_page'] = item.get('page', 1)
                                logger.info(f"📋 Mock found sample_size: {n_val}")
                        except ValueError:
                            pass
                
                # Look for efficacy patterns
                if 'efficacy' in text_lower or '95%' in text or 'effective' in text_lower:
                    if '95' in text:
                        result['primary_endpoint_result']['source_text'] = text
                        coords = item.get('coords', item.get('bbox', [0, 0, 0, 0]))
                        result['primary_endpoint_result']['coords'] = coords
                        result['primary_endpoint_result']['bbox'] = coords
                        result['primary_endpoint_result']['source_page'] = item.get('page', 1)
                        logger.info(f"📋 Mock found efficacy result")
        
        logger.info(f"📋 Mock extraction returned {len(result)} fields: {list(result.keys())}")
        return result