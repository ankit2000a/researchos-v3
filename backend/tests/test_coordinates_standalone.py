import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_architect import DataArchitect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_coordinate_matching():
    da = DataArchitect()
    
    # Test Data matches what prompt would produce
    vision_map = [
        {'text': 'BNT162b2 was 95% effective', 'page': 1, 'coords': [100, 100, 50, 20]},
        {'text': 'Safety profile was good', 'page': 2, 'coords': [200, 200, 60, 30]},
        {'text': 'p<0.001 for the primary endpoint', 'page': 3, 'coords': [300, 300, 70, 40]},
        {'text': 'A total of 43,548 participants were randomized', 'page': 1, 'coords': [400, 400, 80, 50]}
    ]
    
    extracted = {
        'efficacy_rate': {'extracted_value': '95%'},
        'p_value': {'extracted_value': '<0.001'},
        'sample_size': {'extracted_value': 43548},
        'safety': {'extracted_value': 'Safety profile good'} # Fuzzy match
    }
    
    logger.info("Running coordinate matching...")
    linked = da._link_fields_to_coordinates(extracted, vision_map)
    
    # Assertions
    failures = []
    
    # Check Efficacy (Short value fallback or exact match)
    if linked['efficacy_rate']['coords'][0] == 100:
        logger.info("✅ Efficacy matched correctly")
    else:
        logger.error(f"❌ Efficacy match failed: {linked['efficacy_rate']['coords']}")
        failures.append("Efficacy")

    # Check P-Value (Exact match with cleaning)
    if linked['p_value']['coords'][0] == 300:
        logger.info("✅ P-Value matched correctly")
    else:
        logger.error(f"❌ P-Value match failed: {linked['p_value']['coords']}")
        failures.append("P-Value")

    # Check Sample Size (Numeric match 43548 vs 43,548)
    if linked['sample_size']['coords'][0] == 400:
        logger.info("✅ Sample Size matched correctly")
    else:
        logger.error(f"❌ Sample Size match failed: {linked['sample_size']['coords']}")
        failures.append("Sample Size")

    # Check Safety (Fuzzy)
    if linked['safety']['coords'][0] == 200:
        logger.info("✅ Safety matched correctly")
    else:
        logger.error(f"❌ Safety match failed: {linked['safety']['coords']}")
        failures.append("Safety")
        
    if not failures:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n❌ FAILED TESTS: {', '.join(failures)}")
        sys.exit(1)

if __name__ == "__main__":
    test_coordinate_matching()
