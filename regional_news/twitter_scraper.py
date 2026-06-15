import os
import time
import pickle
import random
import re
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright
from config import MEDIA_DIR
from utils import is_seen, mark_seen, get_media_path

import sys
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)
from shared_cookie_manager import get_current_cookie_file, rotate_cookie

def load_cookies(context):
    try:
        cookie_path = get_current_cookie_file()
        if not cookie_path:
            return False
        with open(cookie_path, "rb") as f:
            cookies = pickle.load(f)
        pw_cookies = []
        for c in cookies:
            same_site = c.get("sameSite", "Lax")
            if isinstance(same_site, str):
                if same_site.lower() == "no_restriction":
                    same_site = "None"
                else:
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
        print(f"[!] Error loading Twitter cookies: {e}")
        return False

def scrape_twitter(accounts: List[str], max_age_minutes: int = 31, bypass_seen: bool = False) -> List[Dict[str, Any]]:
    print(f"[*] Starting Twitter Scraper for {len(accounts)} accounts (max_age: {max_age_minutes}m, bypass_seen: {bypass_seen})...")
    results = []
    
    cookie_path = get_current_cookie_file()
    if not cookie_path or not os.path.exists(cookie_path):
        print("[!] Twitter cookies not found. Cannot scrape protected Twitter data.")
        return results

    try:
        with sync_playwright() as p:
            # Added TOR PROXY and CACHE PURGE args
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-gpu", 
                    "--disable-software-rasterizer", 
                    "--disable-dev-shm-usage",
                    "--disable-http-cache",
                    "--disk-cache-size=1",
                    "--media-cache-size=1",
                    "--disable-blink-features=AutomationControlled",
                ]
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            )
            
            if not load_cookies(context):
                print("[!] Failed to load cookies. Exiting Twitter scraper.")
                browser.close()
                return results
                
            for username in accounts:
                print(f"[*] Checking Twitter account: @{username}")
                page = context.new_page()
                try:
                    page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=120000)
                    page.wait_for_selector('article[data-testid="tweet"]', timeout=90000)
                    time.sleep(2)
                    
                    articles = page.query_selector_all('article[data-testid="tweet"]')
                    for art in articles[:10]:
                        is_pinned = False
                        try:
                            context_el = art.query_selector('div[data-testid="socialContext"]')
                            if context_el and "pinned" in context_el.inner_text().lower():
                                is_pinned = True
                        except: pass
                        
                        link_el = art.query_selector('a[href*="/status/"]')
                        if not link_el: continue
                            
                        href = link_el.get_attribute('href')
                        tweet_id = href.split('/')[-1]
                        full_url = f"https://x.com{href}"
                        identifier = f"twitter_{tweet_id}"
                        
                        if not bypass_seen and is_seen("twitter", identifier):
                            continue
                        
                        time_el = art.query_selector("time")
                        if time_el:
                            date = time_el.get_attribute("datetime")
                            try:
                                dt_str = date.replace("Z", "+00:00")
                                dt = datetime.fromisoformat(dt_str)
                                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                                if max_age_minutes > 0 and (datetime.now(timezone.utc) - dt > timedelta(minutes=max_age_minutes)):
                                    continue
                            except: pass
                        else: continue

                        # Expanded detail page
                        text = ""
                        screenshot_path = None
                        try:
                            tweet_page = context.new_page()
                            tweet_page.goto(full_url, wait_until="domcontentloaded", timeout=120000)
                            tweet_page.wait_for_selector('article[data-testid="tweet"]', timeout=90000)
                            time.sleep(2)
                            
                            tweet_art = tweet_page.query_selector('article[data-testid="tweet"]')
                            text_el = tweet_art.query_selector('div[data-testid="tweetText"]')
                            text = text_el.inner_text().strip() if text_el else ""
                            
                            metrics = {}
                            for metric_name, test_id in [("replies", "reply"), ("reposts", "retweet"), ("likes", "like"), ("bookmarks", "bookmark")]:
                                btn = tweet_art.query_selector(f'button[data-testid="{test_id}"]')
                                if btn:
                                    aria = btn.get_attribute("aria-label") or ""
                                    parts = aria.split()
                                    if parts and parts[0].replace(",", "").isdigit():
                                        metrics[metric_name] = parts[0]
                            
                            timestamp = int(time.time() * 1000)
                            screenshot_filename = f"twitter_{username}_{tweet_id}_{timestamp}.png"
                            screenshot_path = get_media_path(screenshot_filename)
                            
                            tweet_art.scroll_into_view_if_needed()
                            time.sleep(1)
                            tweet_art.screenshot(path=screenshot_path)
                            tweet_page.close()
                        except Exception as e:
                            print(f"[-] Failed to load tweet {tweet_id}: {e}")
                            if 'tweet_page' in locals() and not tweet_page.is_closed(): tweet_page.close()
                            continue
                        
                        results.append({
                            "platform": "twitter", "account": username, "url": full_url,
                            "text": text, "date": date, "screenshot": screenshot_path, "metrics": metrics
                        })
                        mark_seen("twitter", identifier)
                        
                except Exception as e:
                    print(f"[-] Error parsing @{username}: {e}")
                finally:
                    if not page.is_closed(): page.close()
                    
            browser.close()
    except Exception as e:
        print(f"[-] Critical error in Twitter scraper: {e}")
        
    return results
