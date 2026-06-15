import pickle
from playwright.sync_api import sync_playwright
import time

def capture_cookies():
    print("====================================")
    print("  TWITTER COOKIE CAPTURE SCRIPT     ")
    print("====================================")
    print("1. A browser window will open.")
    print("2. Log into your new Twitter account manually.")
    print("3. Once you are successfully logged in and on the home feed,")
    print("   come back to this console and press Enter.")
    print("====================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to Twitter login
        page.goto("https://x.com/i/flow/login")
        
        # Wait for user input in the console
        input("\n[!] Press ENTER here *ONLY AFTER* you have fully logged in to Twitter...\n")
        
        # Save cookies
        cookies = context.cookies()
        
        if not cookies:
            print("[-] No cookies found! Did you log in?")
            return
            
        with open("twitter_cookies.pkl", "wb") as f:
            pickle.dump(cookies, f)
            
        print("[+] SUCCESS! New cookies saved to 'twitter_cookies.pkl'.")
        print("[+] You can now run the OSINT scraper again.")
        
        browser.close()

if __name__ == "__main__":
    capture_cookies()
