import sys
import os
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed.")
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1280, "height": 800})
    
    print("Navigating to frontend...")
    page.goto("http://localhost:5173/")
    time.sleep(2)
    
    print("Uploading PDF...")
    pdf_path = "/Users/akshay/Build/ResearchOS_Core/backend/uploads/HON-44-e70167.pdf"
    
    try:
        page.set_input_files('input[type="file"]', pdf_path)
    except Exception as e:
        print("Could not find file input:", e)
        page.screenshot(path="/Users/akshay/Build/ResearchOS_Core/error1.png")
        browser.close()
        sys.exit(1)
    
    print("Waiting for upload to process (timeout 240s)...")
    try:
        # Wait for the processing to finish by looking for 'study title' in the sidebar
        # Using a very generous timeout since Gemini can take up to 4 minutes
        page.wait_for_selector('text="study title"', timeout=240000)
        print("Found Study Title in sidebar!")
        
        # Take a screenshot showing the populated sidebar before clicking
        page.screenshot(path="/Users/akshay/.gemini/antigravity/brain/efadf056-f38d-45bc-9270-6fd5c45dd5dd/sidebar_populated.png")
        print("Captured intermediate sidebar screenshot.")
        
    except Exception as e:
        print("Failed to find result:", e)
        page.screenshot(path="/Users/akshay/Build/ResearchOS_Core/failed_upload.png")
        browser.close()
        sys.exit(1)
        
    time.sleep(2)
    print("Clicking 'View in PDF' for Study Title")
    try:
        # Click the "View in PDF" button / card
        page.click('text="View in PDF"')
    except Exception as e:
        print("Failed to click:", e)
    
    time.sleep(3)
    
    screenshot_path = "/Users/akshay/.gemini/antigravity/brain/efadf056-f38d-45bc-9270-6fd5c45dd5dd/highlight_test_success.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")
    browser.close()
