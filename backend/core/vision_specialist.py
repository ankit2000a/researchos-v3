import os
import json
import logging
from typing import Tuple, List, Dict, Any
from core.config import Config

# try:
#     from unstract.llmwhisperer import LLMWhispererClientV2
# except ImportError:
#     LLMWhispererClientV2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisionSpecialist:
    """
    Agent 1: Vision Specialist (LLMWhisperer V3)
    Goal: Extract text with precise geometric grounding [x, y, w, h].
    """
    def __init__(self):
        self.api_key = Config.LLMWHISPERER_API_KEY
        self.client = None
        # if self.api_key and LLMWhispererClientV2:
        #     self.client = LLMWhispererClientV2(api_key=self.api_key)
        
    def process_pdf(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process PDF and return (Markdown Text, Vision Map).
        Vision Map Format: list of {text, bbox: [x, y, w, h], page}
        """
        if not self.client:
            logger.warning("VisionSpecialist: No API Key or Client found. Using High-Fidelity Mock.")
            return self._mock_process(file_path)
            
        try:
            # Real implementation would be:
            # result = self.client.whisper(file_path, output_mode="layout_preserving", include_coordinates=True)
            # return self._parse_real_response(result)
            pass
        except Exception as e:
            logger.error(f"Vision API Failed: {e}")
            raise

    def _mock_process(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Returns a mock result for 'conflict_study.pdf' to test the Truth Engine.
        """
        logger.info(f"Processing in MOCK mode for {file_path}")
        
        # Narrative Text with a deliberate contradiction for testing
        markdown_text = """
        # Clinical Study Report: Drug X
        
        ## Primary Analysis
        The study included N=500 participants.
        
        Table 1: Efficacy Results
        | Metric | Value | P-Value |
        |---|---|---|
        | Outcome A | 12.5 | 0.04 |
        
        ## Conclusion
        The result was deemed **not statistically significant** due to high variance in the control group.
        """
        
        # Vision Map (Geometry) matches the Table data
        # "0.04" is strictly located at [400, 300, 40, 15]
        vision_map = [
            {"text": "0.04", "bbox": [400, 300, 40, 15], "page": 1, "confidence": 0.98},
            {"text": "500", "bbox": [100, 150, 30, 15], "page": 1, "confidence": 0.99},
            {"text": "Outcome A", "bbox": [50, 300, 80, 15], "page": 1, "confidence": 0.95}
        ]
        
        return markdown_text, vision_map
