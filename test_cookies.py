import os
import glob
import pickle
import time
from playwright.sync_api import sync_playwright

def load_cookies(context, cookie_path):
    print(f"[*] Loading cookies from {cookie_path}")
    try:
        with open(cookie_path, "rb") as f:
            cookies = pickle.load(f)
        pw_cookies = []
        for c in cookies:
            same_site = c.get("sameSite", "Lax")
            if isinstance(same_site, str):
                same_site = same_site.capitalize()
                if same_site not in ["Strict", "Lax", "None"]:
                    same_site = "Lax"
            else:
                same_site = "Lax"
                
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": c.get("expiry", c.get("expirationDate", -1)),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": same_site,
            })
        context.add_cookies(pw_cookies)
        return True
    except Exception as e:
        print(f"[!] Error loading {cookie_path}: {e}")
        return False

def test_cookie_file(cookie_path):
    ret = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        username = None
        twid = None
        try:
            with open(cookie_path, "rb") as f:
                raw_cookies = pickle.load(f)
                for c in raw_cookies:
                    if c["name"] == "twid":
                        twid = c["value"].replace("u%3D", "").replace("u=", "")
        except:
            pass

        if not load_cookies(context, cookie_path):
            browser.close()
            return False, f"TWID: {twid}" if twid else "Unknown"
            
        page = context.new_page()
        try:
            print(f"[*] Navigating to X.com with {cookie_path}...")
            page.goto("https://x.com/home", timeout=30000, wait_until="commit")
            try:
                page.wait_for_selector('div[data-testid="primaryColumn"], a[data-testid="loginButton"]', timeout=8000)
            except:
                pass
            
            # Check for redirect to login or check for unauth elements
            current_url = page.url
            if "i/flow/login" in current_url or "login" in current_url or "signup" in current_url:
                print(f"[-] {cookie_path} explicitly redirected to login.")
                ret = False
            else:
                body_text = page.locator("body").text_content()
                if "Sign in to X" in body_text or "Don’t have an account?" in body_text:
                    print(f"[-] {cookie_path} showed unauthenticated page.")
                    ret = False
                elif "primaryColumn" in page.locator("body").inner_html():
                    print(f"[+] {cookie_path} appears valid!")
                    ret = True
                    # Try to extract username
                    try:
                        profile_link = page.locator('a[data-testid="AppTabBar_Profile_Link"]').first
                        href = profile_link.get_attribute("href")
                        if href:
                            username = href.replace("/", "@")
                    except:
                        pass
                else:
                    print(f"[?] {cookie_path} could not be fully verified, but did not redirect. Marked as PROBABLY VALID.")
                    ret = True
        except Exception as e:
            print(f"[!] Error checking {cookie_path}: {e}")
            ret = False
            
        browser.close()
        
        info = username if username else f"TWID: {twid}"
        return ret, info

def main():
    # Find all cookie files in osint_news_scraper (or current dir)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    osint_dir = os.path.join(base_dir, "osint_news_scraper")
    
    # Try searching in both the root dir and the scraper dir
    patterns = [
        "twitter_cookies*.pkl",
        "cookie*.pkl",
        os.path.join(osint_dir, "twitter_cookies*.pkl"),
        os.path.join(osint_dir, "cookie*.pkl"),
        os.path.join(base_dir, "cookies", "*.pkl")
    ]
    
    cookie_files = []
    for pattern in patterns:
        cookie_files.extend(glob.glob(pattern))
        
    # Deduplicate paths
    cookie_files = list(set([os.path.abspath(f) for f in cookie_files]))
    
    if not cookie_files:
        print("[-] No twitter_cookies*.pkl files found to test.")
        return

    results = []
    print(f"[*] Found {len(cookie_files)} cookie file(s) to test.")
    
    for cf in cookie_files:
        print(f"\n--- Testing {cf} ---")
        is_valid, info = test_cookie_file(cf)
        results.append((cf, is_valid, info))
        
    print("\n--- RESULTS ---")
    for cf, is_valid, info in results:
        status = "WORKING" if is_valid else "FAILED/EXPIRED"
        print(f"{cf}: {status} ({info})")

if __name__ == "__main__":
    main()
