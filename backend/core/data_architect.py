import logging
import json
from typing import Dict, Any
from core.config import Config
from schemas.clinical_trial import ClinicalTrialData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataArchitect:
    """
    Agent 2: Data Architect (Gemini 3 Pro)
    Goal: Structure unstructured text into ClinicalTrialData schema.
    """
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        # In real implementation: 
        # genai.configure(api_key=self.api_key)
        # self.model = genai.GenerativeModel("gemini-1.5-pro") 
    
    def extract_data(self, markdown_text: str) -> Dict[str, Any]:
        """
        Extracts values into a dictionary matching ClinicalTrialData fields.
        """
        if not self.api_key:
            logger.warning("DataArchitect: No API Key. Using Mock Extraction.")
            return self._mock_extract(markdown_text)

        # Real implementation would call Gemini with JSON schema enforcement
        return {}

    def _mock_extract(self, text: str) -> Dict[str, Any]:
        """
        Mock extraction corresponding to the mock PDF.
        """
        # We extract what is written in the table, ignoring the narrative contradiction (that's the Auditor's job to catch)
        return {
            "p_value": { 
                "value": 0.04, 
                "extracted_value": 0.04,
                "source_text": "0.04"
            },
            "sample_size": {
                "value": 500,
                "extracted_value": 500,
                "source_text": "N=500"
            },
            "primary_endpoint_result": {
                "value": "Outcome A",
                "extracted_value": "Outcome A",
                "source_text": "Outcome A"
            }
        }
