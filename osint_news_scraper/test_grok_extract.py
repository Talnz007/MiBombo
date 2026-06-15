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

def test_grok_extract():
    print("[*] Starting Playwright to test Grok Extraction...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if not load_cookies(context):
            return
            
        page = context.new_page()
        try:
            page.goto("https://x.com/i/grok", timeout=30000)
        except Exception as e:
            pass
            
        time.sleep(5)
        
        try:
            textarea = page.wait_for_selector('textarea', timeout=15000)
            if textarea:
                # Long text
                prompt = "A" * 5000 + "\n\n[END OF INPUT]"
                textarea.fill(prompt)
                time.sleep(1)
                textarea.press("Enter")
                
                print("[+] Waiting for response...")
                time.sleep(15)
                
                text_content = page.locator("body").text_content()
                inner_text = page.locator("body").inner_text()
                
                print(f"[+] [END OF INPUT] in text_content: {'[END OF INPUT]' in text_content}")
                print(f"[+] [END OF INPUT] in inner_text: {'[END OF INPUT]' in inner_text}")
                
        except Exception as e:
            print(f"[-] Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    test_grok_extract()
