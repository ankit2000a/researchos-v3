import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_architect import DataArchitect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_migration():
    logger.info("🧪 Starting Migration Verification Test")
    
    da = DataArchitect()
    if not da.client:
        logger.warning("⚠️  Client not initialized (Keys might be missing). Skipping live test.")
        # If API key is missing, we can't test call, but init worked technically (fallback)
        # But for this task, we want to verify the CLIENT init.
        # DataArchitect logic: if no key -> self.client = None.
        # If key -> self.client = Client().
        # Check env var.
        if os.getenv("GOOGLE_API_KEY"):
             logger.error("❌ GOOGLE_API_KEY is present but client is None!")
             sys.exit(1)
        else:
             logger.info("ℹ️  No API Key, skipping live call.")
             return

    logger.info(f"✅ Client Initialized. Type: {type(da.client)}")
    
    # Test API call
    logger.info("📡 Testing API call with new syntax...")
    try:
        # Use a very simple prompt
        response = da._call_gemini_with_retry("Reply with 'OK'", max_retries=1)
        
        if response:
            logger.info(f"✅ API Call Successful. Response: {response.strip()}")
        else:
            logger.error("❌ API Call returned None")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ API Call Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    print("\n🎉 MIGRATION VERIFIED!")

if __name__ == "__main__":
    test_migration()
