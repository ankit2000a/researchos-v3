
import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.abspath("backend"))

# MOCK DEPENDENCIES BEFORE IMPORT
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = MagicMock()
sys.modules["dotenv"] = MagicMock()

from backend.core.auditor import Auditor
from backend.schemas.clinical_trial import ClinicalDataField

# Mock Config
class MockConfig:
    GOOGLE_API_KEY = "fake"
    GEMINI_MODEL = "gemini-1.5-flash"
    LLMWHISPERER_API_KEY = "fake"
    LLMWHISPERER_BASE_URL = "http://fake"
    LOG_DIR = "./logs"

import backend.core.auditor
backend.core.auditor.Config = MockConfig

def test_auditor_geometry_normalization():
    auditor = Auditor("test_session")
    
    # Case 1: Comma match
    # Text in PDF has comma, extraction has comma
    vision_map = [{"text": "43,548", "coords": [10, 10, 100, 20], "page": 1}]
    value = "43,548"
    coords, _ = auditor._verify_geometry(value, vision_map)
    assert coords == [10, 10, 100, 20], "Failed exact comma match"

    # Case 2: Cross formatting (Val has comma, PDF does not)
    # This might happen if Gemini formats it nicely but PDF is raw
    vision_map = [{"text": "43548", "coords": [10, 10, 100, 20], "page": 1}]
    value = "43,548"
    coords, _ = auditor._verify_geometry(value, vision_map)
    assert coords == [10, 10, 100, 20], "Failed to match '43,548' to '43548'"

    # Case 3: Cross formatting (Val raw, PDF has comma)
    vision_map = [{"text": "43,548", "coords": [10, 10, 100, 20], "page": 1}]
    value = "43548"
    coords, _ = auditor._verify_geometry(value, vision_map)
    assert coords == [10, 10, 100, 20], "Failed to match '43548' to '43,548'"

    # Case 4: Spaces (e.g. p < 0.05 vs p<0.05)
    vision_map = [{"text": "p < 0.05", "coords": [5, 5, 50, 10], "page": 1}]
    value = "p<0.05"
    coords, _ = auditor._verify_geometry(value, vision_map)
    assert coords == [5, 5, 50, 10], "Failed to match 'p<0.05' to 'p < 0.05'"

    print("✅ All Auditor normalization tests passed")

if __name__ == "__main__":
    test_auditor_geometry_normalization()
