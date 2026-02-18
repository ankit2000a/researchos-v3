import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLMWhisperer API
    LLMWHISPERER_API_KEY = os.getenv("LLMWHISPERER_API_KEY")
    LLMWHISPERER_BASE_URL = os.getenv("LLMWHISPERER_BASE_URL", "https://llmwhisperer-api.unstract.com/api/v2")
    
    # Google Gemini API
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    # App Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    LOG_DIR = os.getenv("LOG_DIR", "./backend/logs")
    
    # Validation Thresholds
    CONFIDENCE_THRESHOLD_VERIFIED = 0.99
    CONFIDENCE_THRESHOLD_CONFLICT = 0.45
