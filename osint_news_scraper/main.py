import os
import json
import time
import asyncio
import sys
from datetime import datetime, timezone, timedelta

# Add workspace root so shared_dedup is importable from both scrapers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
from shared_dedup import is_duplicate, mark_seen, claim_url

from config import TARGETS_FILE, WHATSAPP_TARGET, WHATSAPP_REGIONAL_GROUP, WHATSAPP_OTHER_GROUP
import twitter_scraper
import website_scraper
from whatsapp_dispatcher import send_whatsapp_pw
from ai_reporter import generate_osint_report, is_relevant_post
from message_processing import process_grok_output

# ──────────────────── helpers ────────────────────

def load_targets():
    if not os.path.exists(TARGETS_FILE):
        print(f"[!] Targets file {TARGETS_FILE} not found!")
        return {}
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)



def display_item(item, idx=0):
    print(f"\n--- NEW OSINT POST #{idx} ---")
    print(f"PLATFORM: {item.get('platform', '').upper()}")
    print(f"SOURCE  : {item.get('account', item.get('channel', item.get('site', 'Unknown')))}")
    print(f"DATE    : {item.get('date')}")
    print(f"URL     : {item.get('url')}")
    print(f"TEXT    : {item.get('text', '')[:200]}...")
    if item.get('screenshot'):
        print(f"IMAGE   : {item.get('screenshot')}")
    if item.get('media'):
        print(f"MEDIA   : {', '.join(item.get('media'))}")
    print("=" * 40)

def cleanup_media(item, img_path):
    """Delete all media files associated with an item."""
    blank_img = os.path.join("output", "blank_msg.png")
    if img_path and img_path != blank_img and os.path.exists(img_path):
        try:
            os.remove(img_path)
            print(f"[*] Cleaned up media: {img_path}")
        except Exception as e:
            print(f"[-] Could not delete {img_path}: {e}")
    for m in item.get('media', []):
        if m != img_path and m != blank_img and os.path.exists(m):
            try:
                os.remove(m)
            except:
                pass

def _append_to_json_log(filepath, new_records, label=""):
    """Safely append records to a JSON log file (load → merge → write)."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    existing = []
        else:
            existing = []
        existing.extend(new_records)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4, ensure_ascii=False)
        print(f"[+] Saved {len(new_records)} {label} records to {os.path.basename(filepath)} "
              f"(total: {len(existing)})")
    except Exception as e:
        print(f"[-] Could not save {label} log ({filepath}): {e}")

# ──────────────────── dispatch ────────────────────

async def dispatch_item(item):
    """
    Format a single item through the AI reporter and send it to WhatsApp.
    Returns a processed record dict for logging/analysis.
    """
    url = item.get('url', 'No URL')
    category_labels = {1: "GLOBAL", 2: "REGIONAL", 3: "OTHER"}

    # Pick the best image for AI processing
    img_path = item.get('screenshot')
    if not img_path and item.get('media'):
        for m in item.get('media'):
            if m.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = m
                break

    # ── AI Processing ─────────────────────────────────────────────────────────
    raw_grok_response = None
    ai_error = None
    try:
        print(f"[*] Passing item to local AI Reporter (isolated subprocess)...")
        import tempfile
        import subprocess
        
        # Write arguments directly to a temp JSON so subprocess can load them cleanly without quote escaping issues
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
            json.dump({"item": item, "img_path": img_path}, tf)
            temp_path = tf.name
            
        script_code = f"""
import json
import sys
import os

# Add to path
sys.path.insert(0, r'{os.path.dirname(os.path.abspath(__file__))}')

from ai_reporter import generate_osint_report

with open(r'{temp_path}', 'r') as f:
    data = json.load(f)

item = data['item']
img_path = data['img_path']

result = generate_osint_report(item, img_path)

with open(r'{temp_path}.out', 'w', encoding='utf-8') as f:
    f.write(result)
"""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py") as tf_py:
            tf_py.write(script_code)
            script_path = tf_py.name

        try:
            # We run python externally so its asyncio loops, greenlets, and threading have 0 contact with the main app
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise Exception(f"Subprocess failed: {stderr.decode()}")
                
            with open(f"{temp_path}.out", "r", encoding="utf-8") as f:
                report = f.read()
        finally:
            try: os.unlink(temp_path)
            except: pass
            try: os.unlink(f"{temp_path}.out")
            except: pass
            try: os.unlink(script_path)
            except: pass
            
        raw_grok_response = report  # Preserve the full unmodified AI output
    except Exception as e:
        print(f"[!] AI Generation Error: {e}")
        report = f"*[OSINT AI ERROR]* Failed to generate report.\n{e}\n{url}"
        ai_error = str(e)

    # ── Prevent 156-Character Grok Error Blind Dispatch ───────────────────────
    if report and "Sorry about that, something didn't go as planned" in report:
        print("[!] FATAL: Grok error string leaked through all retries! Preventing WhatsApp dispatch.")
        # Fall back to raw format to prevent sending just the error message
        raw_date = item.get("date", "Unknown Date")
        platform_name = item.get("platform", "").capitalize()
        source_name = item.get("account", item.get("channel", item.get("site", "Unknown")))
        caption = item.get("text", "No text provided.")
        report = f"*Aoa, sir*\n\n🔶 *Subject : RAW OSINT Update – {raw_date}*\nPlatform: {platform_name} | Account: @{source_name}\n\n🔹 *Raw Post Text*:\n{caption}\n\nLinks:\n- {url}\n\n *Regards*"

    # ── Parse classification from Grok ────────────────────────────────────────
    result = process_grok_output(report)
    category = result.category
    clean_report = result.payload
    priority = result.priority
    print(f"[*] Grok classified this as category {category}: {category_labels.get(category, '?')}")
    print(f"[*] Priority level: {priority} (tag_found={result.priority_found})")

    # ── Route to the correct WhatsApp group ───────────────────────────────────
    if category == 1:
        target_group = WHATSAPP_TARGET          # "Automated news"
    elif category == 2:
        target_group = WHATSAPP_REGIONAL_GROUP  # "Regional news"
    else:
        target_group = WHATSAPP_OTHER_GROUP     # "Other news"

    # ── Send to WhatsApp ──────────────────────────────────────────────────────
    delivery_status = "failed"
    delivery_error = None
    try:
        print(f"[*] Dispatching to WhatsApp -> {target_group}...")
        if img_path and os.path.exists(img_path) and not img_path.endswith("blank_msg.png"):
            await send_whatsapp_pw(target_group, clean_report, img_path)
        else:
            await send_whatsapp_pw(target_group, clean_report, None)
        print("[+] WhatsApp message sent successfully.")
        mark_seen(url, category=category, source="osint_news_scraper")
        delivery_status = "sent"
    except Exception as e:
        print(f"[-] Failed to send WhatsApp message: {e}")
        delivery_error = str(e)

    # Always cleanup media after dispatch (success or fail)
    cleanup_media(item, img_path)

    # ── Build processed record for analysis ───────────────────────────────────
    processed_record = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "source_pipeline": "osint_news_scraper",
        "url": url,
        "platform": item.get("platform", "unknown"),
        "account": item.get("account", item.get("channel", item.get("site", "unknown"))),
        "original_text": item.get("text", ""),
        "scraped_date": item.get("date"),
        "category_id": category,
        "priority": priority,
        "category_label": category_labels.get(category, "UNKNOWN"),
        "target_whatsapp_group": target_group,
        "grok_raw_response": raw_grok_response,
        "whatsapp_message_sent": clean_report,
        "had_image": bool(img_path and os.path.exists(str(img_path or ""))),
        "delivery_status": delivery_status,
        "delivery_error": delivery_error,
        "ai_error": ai_error,
    }
    return processed_record

# ──────────────────── queue consumer ────────────────────

async def dispatch_worker(queue: asyncio.Queue, all_dispatched: list, all_processed: list):
    """Pulls items from the queue and dispatches them one at a time."""
    while True:
        item = await queue.get()
        if item is None:  # poison pill = done
            queue.task_done()
            break
        try:
            display_item(item, len(all_dispatched) + 1)
            processed_record = await dispatch_item(item)
            all_dispatched.append(item)
            if processed_record:
                all_processed.append(processed_record)
            # Dispatcher itself adds post-send cooldown; this is an additional
            # gap between queue items for extra safety
            import random as _rng
            extra_gap = _rng.uniform(15, 30)
            print(f"[*] Queue gap: waiting {extra_gap:.0f}s before next item...")
            await asyncio.sleep(extra_gap)
        except Exception as e:
            print(f"[!] Dispatch error: {e}")
        queue.task_done()

# ──────────────────── scraper wrappers ────────────────────

async def scrape_twitter_to_queue(accounts, queue: asyncio.Queue):
    """Runs the Twitter scraper, filters for relevant posts, and pushes to queue."""
    try:
        results = await asyncio.to_thread(twitter_scraper.scrape_twitter, accounts)
        for item in results:
            url = item.get('url', '')
            # Claim the URL so another scraper/thread doesn't process it simultaneously
            if not claim_url(url, source="osint_news_scraper"):
                print(f"[DEDUP] Skipping already-seen/claimed URL: {url}")
                cleanup_media(item, item.get('screenshot'))
                continue
            if is_relevant_post(item):
                await queue.put(item)
            else:
                print(f"[*] Skipping irrelevant post from @{item.get('account', '?')}: {item.get('text', '')[:80]}...")
                # Cleanup media for skipped items
                cleanup_media(item, item.get('screenshot'))
    except Exception as e:
        print(f"[!] Twitter scraper error: {e}")

async def scrape_websites_to_queue(sites, queue: asyncio.Queue):
    """Runs the website scraper, filters for relevant posts, and pushes to queue."""
    try:
        results = await asyncio.to_thread(website_scraper.scrape_websites, sites)
        for item in results:
            url = item.get('url', '')
            if not claim_url(url, source="osint_news_scraper"):
                print(f"[DEDUP] Skipping already-seen/claimed URL: {url}")
                cleanup_media(item, item.get('screenshot'))
                continue
            if is_relevant_post(item):
                await queue.put(item)
            else:
                print(f"[*] Skipping irrelevant post from {item.get('site', '?')}")
                cleanup_media(item, item.get('screenshot'))
    except Exception as e:
        print(f"[!] Website scraper error: {e}")

async def scrape_ddg_to_queue(queries, queue: asyncio.Queue):
    """Runs the DuckDuckGo news scraper and pushes to queue."""
    try:
        results = await asyncio.to_thread(website_scraper.scrape_duckduckgo_news, queries)
        for item in results:
            url = item.get('url', '')
            if not claim_url(url, source="osint_news_scraper"):
                continue
            if is_relevant_post(item):
                await queue.put(item)
    except Exception as e:
        print(f"[!] DDG scraper error: {e}")

# ──────────────────── main cycle ────────────────────

async def run_cycle():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] starting parallel OSINT scraping cycle...")
    targets = load_targets()

    websites = targets.get("news_websites", [])
    x_accounts = targets.get("x_accounts", [])
    search_queries = targets.get("search_queries", [])

    if not websites and not x_accounts and not search_queries:
        print("[!] No targets configured to scrape.")
        return

    # Shared queue: scrapers push, dispatcher pops
    queue = asyncio.Queue()
    all_dispatched = []    # Raw scraped items
    all_processed  = []    # Grok-processed reports with analysis metadata

    # Start the dispatcher worker (consumes items as they arrive)
    dispatcher = asyncio.create_task(dispatch_worker(queue, all_dispatched, all_processed))

    # Start all scrapers in parallel — they push to the queue as they finish
    scraper_tasks = []
    if x_accounts:
        scraper_tasks.append(asyncio.create_task(scrape_twitter_to_queue(x_accounts, queue)))
    if websites:
        scraper_tasks.append(asyncio.create_task(scrape_websites_to_queue(websites, queue)))
    if search_queries:
        scraper_tasks.append(asyncio.create_task(scrape_ddg_to_queue(search_queries, queue)))

    # Wait for all scrapers to finish
    await asyncio.gather(*scraper_tasks, return_exceptions=True)

    # Send poison pill to stop the dispatcher
    await queue.put(None)
    await dispatcher

    # ── Save results to logs ──────────────────────────────────────────────────
    cc_dir = os.path.join(BASE_DIR, "..", "osint-command-center")

    if all_dispatched:
        print(f"\n[*] Dispatched {len(all_dispatched)} items this cycle.")

        # 1. Raw scraped data (existing file)
        raw_log_file = os.path.join(cc_dir, "osint_latest_news.json")
        _append_to_json_log(raw_log_file, all_dispatched, "raw")

        # 2. Processed Grok reports (new file — for defence/OSINT analysis)
        processed_log_file = os.path.join(cc_dir, "osint_processed_reports.json")
        _append_to_json_log(processed_log_file, all_processed, "processed")
    else:
        print("[*] No new items found in this cycle.")

async def main():
    if not os.path.exists("targets.json"):
        print("[!] Warning: Make sure to fill in targets.json")

    print("==================================================")
    print("      AUTOMATED OSINT NEWS SCRAPER STARTED")
    print("==================================================")

    # Ollama handles model loading — just verify connectivity
    print("[*] Checking Ollama connectivity...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.ok:
            models = [m['name'] for m in resp.json().get('models', [])]
            print(f"[+] Ollama is running. Available models: {models}")
        else:
            print("[!] Ollama responded but may have issues.")
    except Exception as e:
        print(f"[!] Ollama not reachable: {e}. Make sure 'ollama serve' is running.")

    while True:
        try:
            await run_cycle()
        except Exception as e:
            print(f"[!] Error in OSINT cycle: {e}")

        print("[*] Sleeping for 30 minutes (1800 seconds)...")
        await asyncio.sleep(1800)

if __name__ == "__main__":
    asyncio.run(main())
