import os
import json
import time
import asyncio
import sys
from datetime import datetime, timezone, timedelta

# Add workspace root so shared_dedup is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
from shared_dedup import mark_seen, claim_url

from config import TARGETS_FILE
import twitter_scraper
import website_scraper
from whatsapp_dispatcher import send_whatsapp_pw
from ai_reporter import generate_osint_report, is_relevant_post, parse_category

# TEST CONFIGURATION
TEST_WHATSAPP_TARGET = "+923205622747"
TEST_MODE_ENABLED = True # Redirects all output to TEST_WHATSAPP_TARGET

def load_targets():
    if not os.path.exists(TARGETS_FILE):
        return {}
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def display_item(item, idx=0):
    print(f"\n--- [TEST MODE] NEW OSINT POST #{idx} ---")
    print(f"SOURCE  : {item.get('account', item.get('channel', item.get('site', 'Unknown')))}")
    print(f"URL     : {item.get('url')}")
    print("=" * 40)

def cleanup_media(item, img_path):
    blank_img = os.path.join("output", "blank_msg.png")
    if img_path and img_path != blank_img and os.path.exists(img_path):
        try: os.remove(img_path)
        except: pass
    for m in item.get('media', []):
        if m != img_path and m != blank_img and os.path.exists(m):
            try: os.remove(m)
            except: pass

async def dispatch_item(item):
    url = item.get('url', 'No URL')
    img_path = item.get('screenshot')
    if not img_path and item.get('media'):
        for m in item.get('media'):
            if m.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = m
                break

    print(f"[*] AI Analysis for {url}...")
    try:
        report = await asyncio.to_thread(generate_osint_report, item, img_path)
    except Exception as e:
        print(f"[!] AI Error: {e}")
        return None

    category, clean_report = parse_category(report)
    
    # [TEST REDIRECT]
    target = TEST_WHATSAPP_TARGET
    print(f"[*] Dispatching to TEST TARGET: {target}")

    try:
        await send_whatsapp_pw(target, clean_report, img_path)
        mark_seen(url, category=category, source="regional_news_test")
    except Exception as e:
        print(f"[-] WhatsApp Error: {e}")

    cleanup_media(item, img_path)
    return True

async def dispatch_worker(queue: asyncio.Queue):
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
        try:
            display_item(item)
            await dispatch_item(item)
            await asyncio.sleep(5) # Throttle
        except Exception as e:
            print(f"[!] Worker Error: {e}")
        queue.task_done()

async def run_cycle():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting Scrape Cycle...")
    
    # [FORCE COOKIE] Set to the Firefox cookies specifically
    from shared_cookie_manager import COOKIES_DIR
    target_cookie = "twitter_cookies_firefox.pkl"
    with open(os.path.join(COOKIES_DIR, "current_cookie_index.txt"), "w") as f:
        # Find the index of this cookie
        import glob
        all_cookies = sorted(glob.glob(os.path.join(COOKIES_DIR, "*.pkl")))
        try:
            idx = [os.path.basename(c) for c in all_cookies].index(target_cookie)
            f.write(str(idx))
            print(f"[*] Forced current cookie to: {target_cookie} (Index {idx})")
        except ValueError:
            print(f"[!] {target_cookie} not found in {COOKIES_DIR}")
    
    queue = asyncio.Queue()
    worker = asyncio.create_task(dispatch_worker(queue))

    # [TEST OVERRIDE] Push fake items to test AI and WhatsApp dispatch
    fake_items = [
        {
            "account": "TestAlerts",
            "url": "https://x.com/TestAlerts/status/111",
            "content": "URGENT: A massive 8.0 magnitude earthquake has struck the coast of Japan. Tsunami warnings issued for the entire Pacific rim.",
            "media": []
        },
        {
            "account": "GlobalNews",
            "url": "https://x.com/GlobalNews/status/222",
            "content": "BREAKING: New experimental fusion reactor in France achieves sustained net positive energy for over 24 hours, marking a historic breakthrough in clean energy.",
            "media": []
        }
    ]
    
    for item in fake_items:
        await queue.put(item)

    await queue.put(None)
    await worker

async def main():
    print("==================================================")
    print("      ROBUST OSINT TEST HARNESS")
    print("==================================================")
    
    while True:
        await run_cycle()
        print("\n[*] Cycle complete. Sleeping 10m...")
        await asyncio.sleep(600)

if __name__ == "__main__":
    asyncio.run(main())
