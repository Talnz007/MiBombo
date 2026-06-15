import time
from playwright.sync_api import sync_playwright
import pickle
import glob

def test_grok_dom():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        with open(sorted(glob.glob("twitter_cookies*.pkl"))[0], "rb") as f:
            cookies = pickle.load(f)
        pw_cookies = []
        for c in cookies:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": c.get("expiry", c.get("expirationDate", -1)),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "Lax"),
            })
        context.add_cookies(pw_cookies)
            
        page = context.new_page()
        page.goto("https://x.com/i/grok", timeout=30000)
        time.sleep(5)
        
        textarea = page.locator('textarea').first
        textarea.fill("Hello Grok, what is 2+2? Answer in one word.")
        time.sleep(1)
        textarea.press("Enter")
        time.sleep(10)
        
        html = page.locator("body").inner_html()
        with open("grok_test_dom.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        browser.close()

if __name__ == "__main__":
    test_grok_dom()
