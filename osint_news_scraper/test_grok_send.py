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

def test_grok_send():
    print("[*] Starting Playwright to test Grok Send...")
    with sync_playwright() as p:
        # Note: changing to headless=True since tests seem to run fine headless as well.
        # But using headless=False is good for visual debugging if we run it interactively, here we just snap screenshots.
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if not load_cookies(context):
            return
            
        page = context.new_page()
        page.goto("https://x.com/i/grok")
        
        time.sleep(5)
        page.screenshot(path="grok_step1_loaded.png")
        print("[+] Saved grok_step1_loaded.png")
        
        # Find textarea
        try:
            textarea = page.wait_for_selector('textarea', timeout=10000)
            if textarea:
                print("[+] Found textarea. Typing message...")
                textarea.fill("Hello Grok, please respond with the exact word: BINGO.")
                time.sleep(1)
                page.screenshot(path="grok_step2_filled.png")
                
                # Check for a "Submit" or "Send" button specifically for Grok.
                # Usually it has aria-label="Grok Something" or it's a svg button next to the textarea.
                textarea.press("Enter")
                print("[+] Pressed Enter.")
                time.sleep(3)
                page.screenshot(path="grok_step3_after_enter.png")
                
                print("[+] Waiting for response...")
                time.sleep(15)
                
                page.screenshot(path="grok_step4_final.png")
                print("[+] Saved grok_step4_final.png")
                
                # Dump HTML to inspect structure
                html = page.content()
                with open("grok_dump.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("[+] Saved grok_dump.html")
        except Exception as e:
            print(f"[-] Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    test_grok_send()
