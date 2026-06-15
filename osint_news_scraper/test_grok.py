import os
import time
import pickle
from playwright.sync_api import sync_playwright

TWITTER_COOKIES_PATH = "h:/automatingmework/investigations/twitter_cookies.pkl"

def load_cookies(context):
    try:
        with open(TWITTER_COOKIES_PATH, "rb") as f:
            cookies = pickle.load(f)
        pw_cookies = []
        for c in cookies:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": c.get("expiry", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "Lax"),
            })
        context.add_cookies(pw_cookies)
        return True
    except Exception as e:
        print(f"[!] Error loading Twitter cookies: {e}")
        return False

def test_grok():
    print("[*] Starting Playwright to test Grok...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if not load_cookies(context):
            print("[!] Failed to load cookies.")
            return
            
        page = context.new_page()
        print("[*] Navigating to Grok...")
        page.goto("https://x.com/i/grok")
        
        # Wait a bit
        time.sleep(5)
        
        # Determine what selectors are present
        print("[*] Page loaded. Checking for Grok text area...")
        try:
            # The text area on Grok is usually a textarea or a contenteditable div
            textarea_locators = [
                'textarea[placeholder*="Ask Grok"]',
                'textarea',
                'div[contenteditable="true"]',
                '[data-testid="grok-text-input"]',
                '[data-testid="tweetTextarea_0"]',
                '[aria-label="Ask Grok"]'
            ]
            
            found = False
            for loc in textarea_locators:
                el = page.query_selector(loc)
                if el:
                    print(f"[+] Found text area with locator: {loc}")
                    found = True
                    break
            
            if not found:
                print("[-] Could not find text area.")
                # Maybe take a screenshot
                page.screenshot(path="grok_test.png")
                print("[*] Saved screenshot to grok_test.png")
                
        except Exception as e:
            print(f"[-] Error: {e}")
        
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    test_grok()
