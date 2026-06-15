import time
from playwright.sync_api import sync_playwright
import pickle
import glob

def test_grok_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        
        with open("twitter_cookies_2.pkl", "rb") as f:
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
                "sameSite": "Lax",
            })
        context.add_cookies(pw_cookies)
            
        page = context.new_page()
        page.goto("https://x.com/i/grok", timeout=30000)
        time.sleep(5)
        
        textarea = page.locator('textarea').first
        textarea.fill("Hello Grok, simply reply with the text: **BINGO BONGO** in bold markdown.")
        time.sleep(1)
        textarea.press("Enter")
        
        for i in range(30):
            time.sleep(2)
            if page.locator("button[aria-label='Copy text']").count() > 0:
                break
                
        # Now find the last message content
        # Grok messages are usually within <div class="markdown dir-auto"> or similar
        items = page.locator(".markdown").all()
        if items:
            last_msg = items[-1]
            html = last_msg.inner_html()
            with open("grok_test.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved grok_test.html with markdown wrapper!")
        else:
            print("Could not find .markdown class. Saving full body.")
            with open("grok_test.html", "w", encoding="utf-8") as f:
                f.write(page.locator("body").inner_html())
            
        browser.close()

if __name__ == "__main__":
    test_grok_html()
