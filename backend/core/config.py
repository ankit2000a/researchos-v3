from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LLMWHISPERER_API_KEY = os.getenv("LLMWHISPERER_API_KEY")
    LOG_DIR = os.getenv("LOG_DIR", "./backend/logs")
    
    # Validation Thresholds
    CONFIDENCE_THRESHOLD_VERIFIED = 0.99
    CONFIDENCE_THRESHOLD_CONFLICT = 0.45
