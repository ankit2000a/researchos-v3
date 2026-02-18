import os
import json
import logging
import requests
import time
from typing import Tuple, List, Dict, Any
from core.config import Config
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisionSpecialist:
    """
    Agent 1: Vision Specialist (LLMWhisperer via HTTP)
    Extracts text with precise geometric coordinates [x, y, w, h] from PDFs. 
    """
    def __init__(self):
        self.api_key = os.getenv("LLMWHISPERER_API_KEY") or Config.LLMWHISPERER_API_KEY
        self.base_url = Config.LLMWHISPERER_BASE_URL
        
        if self.api_key:
            logger.info("✅ LLMWhisperer API Key loaded successfully")
        else:
            logger.warning("⚠️  No LLMWhisperer API Key found - will use MOCK mode")
        
    def process_pdf(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Main entry point:  Upload PDF and retrieve extraction"""
        
        if not self.api_key:
            logger.warning("⚠️ No LLMWhisperer API key.  Using MOCK mode")
            return self._mock_process(file_path)
        
        try:
            # Step 1: Upload PDF
            logger.info(f"🚀 Processing PDF with LLMWhisperer: {os.path.basename(file_path)}")
            whisper_hash = self._upload_pdf(file_path)
            
            # Step 2: Poll for results (with proper waiting)
            # Max wait 3 minutes
            result = self._get_result(whisper_hash, max_wait=180) 
            
            # Step 3: Extract data
            narrative = self._extract_text_from_response(result)
            vision_map = self._create_vision_map_from_response(result)
            
            if not narrative:
                logger.warning("⚠️ Empty narrative from LLMWhisperer, using mock")
                return self._mock_process(file_path)
            
            return narrative, vision_map
            
        except Exception as e:
            logger.error(f"❌ LLMWhisperer API Failed: {e}")
            logger.warning("⤵️ Falling back to MOCK mode")
            return self._mock_process(file_path)

    def _upload_pdf(self, file_path:  str) -> str:
        """Upload PDF to LLMWhisperer and return whisper_hash"""
        url = f"{self. base_url}/whisper"
    
        headers = {
            "unstract-key":  self.api_key,
            "Content-Type": "application/pdf"  # KEY FIX! 
        }
        
        params = {
            "output_mode": "layout_preserving",
            "page_seperator": "<<<",
            "processing_mode": "ocr",
            "line_splitter_tolerance": 0.4,
            "horizontal_stretch_factor": 1.0
        }
        
        # Read entire file into memory as raw bytes
        with open(file_path, 'rb') as f:
            pdf_data = f.read()
        
        # Send raw binary data (NOT multipart form-data)
        response = requests.post(
            url, 
            headers=headers, 
            params=params, 
            data=pdf_data,  # KEY FIX:  Use 'data=' not 'files='
            timeout=60
        )
        
        response.raise_for_status()
        data = response.json()
        
        whisper_hash = data. get('whisper_hash') or data.get('whisper-hash')
        
        if not whisper_hash:
            logger.error(f"No whisper_hash in response: {data}")
            raise ValueError("No whisper_hash returned")
        
        logger.info(f"✅ PDF uploaded successfully | whisper_hash: {whisper_hash[: 12]}...")
        return whisper_hash

    def _get_result(self, whisper_hash: str, max_wait: int = 180) -> Dict:
        """Poll LLMWhisperer for extraction result with proper status handling"""
        
        status_url = f"{self.base_url}/whisper-status"
        retrieve_url = f"{self.base_url}/whisper-retrieve"
        
        headers = {
            "unstract-key": self.api_key
        }
        
        params = {
            "whisper_hash": whisper_hash
        }
        
        start_time = time.time()
        attempt = 0
        
        logger.info(f"🔍 Starting retrieval for hash: {whisper_hash[:12]}...")
        
        while time.time() - start_time < max_wait:
            attempt += 1
            
            try:
                logger.debug(f"📡 Status check (attempt {attempt})...")
                response = requests.get(status_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', '').lower()
                    message = data.get('message', '')
                    
                    logger.debug(f"Response status field: '{status}'")
                    
                    # SUCCESS: Processing complete - NOW FETCH THE ACTUAL TEXT
                    if status in ['processed', 'completed', 'done']:
                        logger.info(f"✅ Processing complete after {attempt} attempts! Fetching text...")
                        
                        # CRITICAL: Call the retrieve endpoint to get actual text
                        retrieve_response = requests.get(
                            retrieve_url, 
                            headers=headers, 
                            params=params, 
                            timeout=60
                        )
                        retrieve_response.raise_for_status()
                        
                        # The retrieve endpoint returns the extracted text
                        # Check if response is JSON or plain text
                        content_type = retrieve_response.headers.get('Content-Type', '')
                        
                        if 'application/json' in content_type: 
                            retrieve_data = retrieve_response.json()
                            
                            # DEBUG LOGGING for Issue 3
                            logger.info(f"📋 Response keys: {list(retrieve_data.keys())}")
                            if 'line_metadata' in retrieve_data:
                                logger.info(f"📋 Line metadata sample (first 3 items): {json.dumps(retrieve_data['line_metadata'][:3], indent=2)}")
                            if 'metadata' in retrieve_data:
                                logger.info(f"📋 Metadata: {json.dumps(retrieve_data['metadata'], indent=2)[:500]}")
                            
                            text = self._extract_text_from_response(retrieve_data)
                            vision_map = self._create_vision_map_from_response(retrieve_data)
                        else:
                            # Plain text response
                            text = retrieve_response.text
                            vision_map = []
                        
                        if text and len(text) > 10: 
                            logger.info(f"✅ Extracted {len(text)} characters from LLMWhisperer")
                            logger.info(f"✅ Created vision map with {len(vision_map)} data points")
                            
                            return {
                                "text": text,
                                "vision_map": vision_map,
                                "status": "processed"
                            }
                        else: 
                            logger.warning(f"Retrieved text too short ({len(text) if text else 0} chars)")
                            raise ValueError("Empty or too short text retrieved")
                    
                    # PROCESSING: Still working on it
                    elif status in ['processing', 'pending', 'queued', 'ingesting']:
                        logger.info(f"⏳ Still processing... (attempt {attempt}) - waiting 5 seconds")
                        time.sleep(5)
                        continue
                    
                    # FAILED: Fatal error
                    elif status in ['failed', 'error']: 
                        error_msg = data.get('error', message or 'Unknown error')
                        logger.error(f"❌ LLMWhisperer processing failed: {error_msg}")
                        raise ValueError(f"LLMWhisperer failed: {error_msg}")
                    
                    # UNKNOWN STATUS: Check message for clues
                    else: 
                        if any(phrase in message.lower() for phrase in ['not ready', 'ingestion', 'processing']):
                            logger.info(f"⏳ PDF still being processed ('{message}') - waiting 5 seconds")
                            time.sleep(5)
                            continue
                        else:
                            logger.warning(f"Unknown status '{status}', message: '{message}' - waiting 5 seconds")
                            time.sleep(5)
                            continue
                
                # 202 Accepted = still processing
                elif response.status_code == 202:
                    logger.info(f"⏳ Processing (HTTP 202)... (attempt {attempt}) - waiting 5 seconds")
                    time.sleep(5)
                    continue
                
                # 400 Bad Request - check if it's "not ready" or real error
                elif response.status_code == 400:
                    try:
                        error_data = response.json()
                        message = error_data.get('message', '')
                        
                        if 'not ready' in message.lower() or 'ingestion' in message.lower():
                            logger.info(f"⏳ Ingestion in progress ('{message}') - waiting 5 seconds")
                            time.sleep(5)
                            continue
                        else:
                            logger.error(f"❌ 400 Bad Request: {message}")
                            response.raise_for_status()
                    except:
                        logger.error(f"❌ 400 Bad Request: {response.text[:500]}")
                        response.raise_for_status()
                
                else:
                    logger.error(f"❌ Unexpected status {response.status_code}: {response.text[:500]}")
                    response.raise_for_status()
            
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Request timeout on attempt {attempt}, retrying...")
                time.sleep(3)
                continue
            
            except requests.exceptions.RequestException as e: 
                logger.error(f"❌ Request failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text[:500]}")
                raise
        
        raise TimeoutError(f"Extraction timed out after {max_wait} seconds ({attempt} attempts)")

    def _extract_text_from_response(self, data: Dict) -> str:
        """Extract text from LLMWhisperer response - try all possible locations"""
        import json
        
        # ✅ PRIMARY FIX: LLMWhisperer v2 API uses 'result_text' field
        if 'result_text' in data:
            text = data['result_text']
            if text and isinstance(text, str) and len(text) > 0:
                return text
        
        # Fallback:  Try other common field names
        if 'detail' in data:
            detail = data['detail']
            if isinstance(detail, str) and len(detail) > 0:
                return detail
            elif isinstance(detail, dict):
                text = detail.get('text', '') or detail.get('extraction', '') or detail.get('result_text', '')
                if text: 
                    return text
        
        if 'result' in data: 
            result = data['result']
            if isinstance(result, dict):
                text = (
                    result.get('text', '') or 
                    result.get('extraction', '') or 
                    result.get('result_text', '') or
                    result.get('extracted_text', '')
                )
                if text: 
                    return text
            elif isinstance(result, str) and len(result) > 0:
                return result
        
        if 'text' in data:
            text = data['text']
            if text: 
                return text
        
        if 'extraction' in data: 
            extraction = data['extraction']
            if isinstance(extraction, dict):
                text = extraction.get('text', '') or extraction.get('result_text', '')
                if text:
                    return text
            elif isinstance(extraction, str) and len(extraction) > 0:
                return extraction
        
        if 'extracted_text' in data:
            text = data['extracted_text']
            if text:
                return text
        
        if 'content' in data:
            text = data['content']
            if text:
                return text
        
        # Failed to find text - log for debugging
        logger.warning(f"Could not find text in response.  Keys present: {list(data.keys())}")
        logger.debug(f"Response structure (first 1000 chars): {json.dumps(data, indent=2)[:1000]}")
        
        return ''

    def _create_vision_map_from_response(self, data: Dict) -> List[Dict]:
        """Extract coordinates from LLMWhisperer line_metadata"""
        import json
        
        vision_map = []
        
        # LLMWhisperer v2 format: line_metadata is array of [x, y, width, height]
        if 'line_metadata' not in data:
            logger.warning("No line_metadata in LLMWhisperer response")
            # Fallback to older formats
            if 'layout' in data:
                return self._parse_legacy_layout(data['layout'])
            return vision_map
        
        line_metadata = data['line_metadata']
        result_text = data.get('result_text', '')
        
        # Split text into lines to match with coordinates
        lines = result_text.split('\n')
        
        logger.info(f"📐 Processing {len(line_metadata)} coordinate boxes for {len(lines)} text lines")
        
        valid_boxes = 0
        
        for idx, bbox in enumerate(line_metadata):
            # bbox format: [x, y, width, height]
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            
            x, y, w, h = bbox
            
            # Skip invalid boxes (all zeros or negative values)
            if (x == 0 and y == 0 and w == 0 and h == 0) or w <= 0 or h <= 0:
                continue
            
            # Get corresponding text line
            text_line = lines[idx].strip() if idx < len(lines) else ''
            
            # Skip empty lines
            if not text_line:
                continue
            
            # Estimate page number based on y-coordinate
            # Typical page height is ~3000-4000 pixels in LLMWhisperer
            # This is a heuristic; ideally LLMWhisperer returns page numbers in metadata
            page_height = 3024  
            page_num = (y // page_height) + 1
            
            # Normalize y to page-relative coordinate
            y_on_page = y % page_height
            
            vision_map.append({
                'id': f'line_{idx}',
                'type': 'text',
                'value': text_line,
                'page': page_num,
                'x': x,
                'y': y_on_page,
                'w': w,
                'h': h,
                'coords': [x, y_on_page, w, h] # Ensure flat coords exist for legacy code
            })
            
            valid_boxes += 1
            
        logger.info(f"✅ Created vision map with {valid_boxes} coordinate points from {len(line_metadata)} boxes")
        
        return vision_map

    def _parse_legacy_layout(self, layout: List) -> List[Dict]:
        """Fallback for legacy layout format"""
        vision_map = []
        if isinstance(layout, list):
            for item in layout:
                if isinstance(item, dict):
                    vision_map.append({
                        'type': item.get('type', 'text'),
                        'value': item.get('text', ''),
                        'coords': item.get('bbox', [0,0,0,0]),
                        'page': item.get('page', 0)
                    })
        return vision_map

    def _mock_process(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """High-fidelity mock for testing without API key"""
        logger.info(f"📋 Running in MOCK mode for: {os.path.basename(file_path)}")
        
        narrative_text = """
        Clinical Study Report: Drug X Efficacy Trial
        
        Table 1: Primary Efficacy Results
        ----------------------------------------
        Metric              Value    P-Value
        Outcome A           12.5     0.04
        Outcome B           8.3      0.12
        
        Results Summary:
        The primary endpoint, Outcome A, showed a mean improvement of 12.5 points 
        in the treatment group compared to placebo. However, this difference was 
        not statistically significant (p>0.05) after adjustment for multiple comparisons.
        
        Study Design: 
        - Sample Size: N=500 (Treatment: 250, Placebo: 250)
        - Duration: 12 weeks
        - Primary Endpoint: Change in Outcome A from baseline
        
        Conclusion:
        While numerical improvements were observed, the results do not support 
        statistical significance for the primary endpoint.
        """
        
        vision_map = [
            {"text": "0.04", "bbox": [400, 300, 40, 15], "page": 1, "field": "p_value"},
            {"text": "500", "bbox": [100, 150, 30, 15], "page": 1, "field": "sample_size"},
            {"text": "Outcome A", "bbox": [50, 300, 80, 15], "page": 1, "field": "primary_endpoint_result"},
            {"text": "12.5", "bbox": [350, 300, 40, 15], "page": 1, "field": "outcome_value"},
            {"text": "not statistically significant", "bbox": [50, 450, 200, 15], "page": 1, "field": "narrative_claim"}
        ]
        
        return narrative_text, vision_map
