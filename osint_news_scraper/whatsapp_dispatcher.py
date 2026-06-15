import os
import re
import asyncio
import random
import json
import shutil
from datetime import datetime, timedelta
if os.name == 'nt':
    import msvcrt
else:
    import fcntl
from playwright.async_api import async_playwright

# ──────────────────── SAFETY CONFIGURATION ────────────────────
# These limits protect the WhatsApp account from being flagged
MAX_MESSAGES_PER_HOUR_GLOBAL = 5   # Hourly cap for Global/Automated news
MAX_MESSAGES_PER_HOUR_REGIONAL = 20 # Hourly cap for Regional news
MAX_MESSAGES_PER_HOUR_DEFAULT = 25  # Fallback
# Daily cap removed to prevent missing critical messages
MIN_DELAY_BETWEEN_MSG = 10      # Minimum seconds between messages
MAX_DELAY_BETWEEN_MSG = 25      # Maximum seconds between messages (randomized)
SESSION_COOLDOWN_ON_ERROR = 120 # Seconds to wait after an error before retrying
MESSAGE_TYPING_DELAY  = 0.03    # Seconds between each character "typed" (human simulation)

# Updated user-agent to match current Chrome stable (less suspicious)
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"

# ──────────────────── RATE LIMITER ────────────────────

# Shared session path — ONE session for the entire workspace at project root
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_SESSION_DIR = os.path.join(WORKSPACE_DIR, "whatsapp_session")
RATE_LIMIT_FILE = os.path.join(WORKSPACE_DIR, "whatsapp_rate_limit.json")
SESSION_BACKUP_DIR = os.path.join(WORKSPACE_DIR, "whatsapp_session_backup")

def _get_hourly_limit(group_name: str) -> int:
    name = group_name.lower()
    if "global" in name or "automated news" in name:
        return MAX_MESSAGES_PER_HOUR_GLOBAL
    elif "regional" in name:
        return MAX_MESSAGES_PER_HOUR_REGIONAL
    return MAX_MESSAGES_PER_HOUR_DEFAULT

def _load_rate_data():
    """Load rate limiting data from disk."""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, "r") as f:
                data = json.load(f)
                if "messages" in data and isinstance(data["messages"], list):
                    # Migrate old list format to dict format
                    data["messages"] = {"default": data["messages"]}
                elif "messages" not in data:
                    data = {"messages": {}}
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return {"messages": {}}

def _save_rate_data(data):
    """Persist rate limiting data to disk."""
    try:
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"[!] Could not save rate limit data: {e}")

def _check_rate_limit(group_name: str = "default"):
    """
    Returns (allowed: bool, wait_seconds: float).
    """
    data = _load_rate_data()
    now = datetime.now()
    
    # Prune messages older than 1 hour across all categories to keep file size small
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    for cat in list(data["messages"].keys()):
        data["messages"][cat] = [ts for ts in data["messages"][cat] if ts > cutoff_hour]

    # Count messages for specifically this group in the last hour
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    
    group_msgs = data["messages"].get(cat_id, [])
    msgs_last_hour = [ts for ts in group_msgs if ts > cutoff_hour]
    
    hourly_limit = _get_hourly_limit(group_name)
    
    if len(msgs_last_hour) >= hourly_limit:
        oldest_hour = min(msgs_last_hour)
        expire_at = datetime.fromisoformat(oldest_hour) + timedelta(hours=1)
        wait = (expire_at - now).total_seconds()
        print(f"[RATE LIMIT] Hourly cap reached for {group_name} ({len(msgs_last_hour)}/{hourly_limit}). "
              f"Must wait {wait/60:.1f} minutes.")
        return False, max(wait, 30)

    return True, 0

def _record_message(group_name: str = "default"):
    """Record that a message was sent (for rate limiting)."""
    data = _load_rate_data()
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    
    if cat_id not in data["messages"]:
        data["messages"][cat_id] = []
        
    data["messages"][cat_id].append(datetime.now().isoformat())
    _save_rate_data(data)

def get_rate_limit_status(group_name: str = "default"):
    """Public helper: returns (msgs_last_hour_for_group, 0) for monitoring."""
    data = _load_rate_data()
    now = datetime.now()
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    group_msgs = data["messages"].get(cat_id, [])
    
    msgs_hour = len([ts for ts in group_msgs if ts > cutoff_hour])
        
    return msgs_hour, 0

# ──────────────────── SESSION BACKUP ────────────────────

def backup_session():
    """Create a backup of the session directory before launching the browser."""
    if not os.path.exists(SHARED_SESSION_DIR):
        print("[!] No session directory to back up.")
        return False
    try:
        if os.path.exists(SESSION_BACKUP_DIR):
            # Keep the last backup — don't nuke it if the new one fails
            pass
        else:
            shutil.copytree(SHARED_SESSION_DIR, SESSION_BACKUP_DIR,
                          dirs_exist_ok=False)
            print(f"[+] Session backed up to {SESSION_BACKUP_DIR}")
        return True
    except Exception as e:
        print(f"[!] Session backup failed (non-fatal): {e}")
        return False

# ──────────────────── TEXT CLEANER ────────────────────

def clean_osint_report(text: str) -> str:
    """
    Cleans rogue AI markdown while preserving Grok's native WhatsApp formatting.
    Keeps *bold*, 🔹/🔶 emojis, and proper spacing intact.
    """
    # 1. Strip local AI thought blocks (e.g., **Thought for 45s** or <think> tags)
    text = re.sub(r'\*\*Thought for.*?\*\*\n*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<think>.*?</think>\n*', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Unwrap messy Markdown links: [**URL**](/URL) -> URL
    text = re.sub(r'\[\*\*?(https?://[^\s\]]+)\*\*?\]\(.*?\)', r'\1', text)
    text = re.sub(r'\[(https?://[^\s\]]+)\]\(.*?\)', r'\1', text)
    
    # 3. Convert markdown bold **text** to WhatsApp bold *text*
    #    (DOM fallback path produces **bold** via markdownify)
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
    
    # 4. Fix any leftover triple+ asterisks (from nested spans) down to single *
    text = re.sub(r'\*{3,}([^*]+)\*{3,}', r'*\1*', text)
    text = re.sub(r'\*{3,}', '*', text)
    
    # 5. Clean up redundant spaces and excessive blank lines
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

# ──────────────────── MAIN DISPATCHER ────────────────────

async def send_whatsapp_pw(group_name: str, message: str, image_path: str = None):
    """
    Sends a WhatsApp message using a persistent Chromium browser managed by Playwright.
    Uses the SHARED session at the project root level.
    
    Safety features:
    - Rate limiting (per-hour and per-day caps)
    - Randomized human-like delays between actions
    - Session backup before browser launch
    - Graceful error handling with cooldown
    - Updated, platform-matching user-agent
    """
    # === APPLY THE CLEANER HERE ===
    message = clean_osint_report(message)

    # === RATE LIMIT CHECK ===
    allowed, wait_time = _check_rate_limit(group_name)
    if not allowed:
        print(f"[RATE LIMIT] Skipping message to '{group_name}' — rate limit active.")
        print(f"[RATE LIMIT] Would need to wait {wait_time/60:.1f} minutes. Dropping this message.")
        return  # Don't queue/retry, just skip to be safe

    # === SESSION VALIDATION ===
    if not os.path.exists(SHARED_SESSION_DIR):
        print(f"[!] CRITICAL: Shared session directory not found at {SHARED_SESSION_DIR}")
        print(f"[!] Cannot send WhatsApp messages without a valid session.")
        raise FileNotFoundError(f"WhatsApp session not found: {SHARED_SESSION_DIR}")

    # === BACKUP SESSION (first run only — if backup doesn't exist) ===
    if not os.path.exists(SESSION_BACKUP_DIR):
        backup_session()

    # === GLOBAL LOCK ===
    lock_file_path = os.path.join(WORKSPACE_DIR, "whatsapp_global.lock")
    lock_fd = open(lock_file_path, "w")
    
    print(f"[*] Trying to acquire global WhatsApp lock...")
    while True:
        try:
            if os.name == 'nt':
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            print(f"[+] Lock acquired! Launching WhatsApp...")
            break
        except (IOError, BlockingIOError):
            print(f"[-] Another scraper is using WhatsApp. Waiting 5s...")
            await asyncio.sleep(5)

    try:
        # === ADD HUMAN-LIKE JITTER BEFORE LAUNCHING ===
        pre_launch_delay = random.uniform(2, 5)
        print(f"[*] Pre-launch delay: {pre_launch_delay:.1f}s")
        await asyncio.sleep(pre_launch_delay)

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=SHARED_SESSION_DIR,
                headless=False,
                viewport={"width": 1280, "height": 900},
                user_agent=USER_AGENT,
                args=[
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                ignore_default_args=["--enable-automation"],
            )
            
            page = await browser.new_page()

            # Remove the webdriver flag that WhatsApp/Meta can detect
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            try:
                print(f"[*] Opening WhatsApp Web to find '{group_name}'...")
                await page.goto("https://web.whatsapp.com/", timeout=60000)
                
                # === WAIT FOR LOGIN ===
                search_selector = 'input[aria-label="Search or start a new chat"]'
                try:
                    await page.wait_for_selector(search_selector, timeout=30000)
                except:
                    print("[!] Please scan the QR code. Waiting 90s...")
                    await page.wait_for_selector(search_selector, timeout=90000)
                    print("[+] Logged in!")
                    await asyncio.sleep(5)

                # === HUMAN-LIKE SEARCH ===
                await asyncio.sleep(random.uniform(1, 3))  # Pause before searching
                await page.fill(search_selector, group_name)
                await asyncio.sleep(random.uniform(2, 4))  # Wait for results
                
                chat_title = f'span[title="{group_name}"]'
                await page.wait_for_selector(chat_title, timeout=10000)
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Human pause before clicking
                await page.click(chat_title)
                await asyncio.sleep(random.uniform(2, 4))  # Wait for chat to load
                
                msg_box_selector = 'div[role="textbox"][aria-label^="Type a message"]'
                await page.wait_for_selector(msg_box_selector, timeout=10000)
                
                has_image = image_path and os.path.exists(image_path) and "blank_msg.png" not in image_path
                
                if has_image:
                    # === STEP 1: Click the Attach (+) button ===
                    attach_sel = 'button[aria-label="Attach"], span[data-icon="plus-rounded"]'
                    await page.wait_for_selector(attach_sel, timeout=20000)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await page.click(attach_sel)
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # === STEP 2: Click "Photos & videos" and handle file chooser ===
                    async with page.expect_file_chooser(timeout=10000) as fc_info:
                        await page.click('text="Photos & videos"')
                    
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(image_path)
                    print(f"[*] Image selected: {os.path.basename(image_path)}")
                    
                    # === STEP 3: Wait for preview, then send ===
                    await asyncio.sleep(random.uniform(3, 5))
                    await page.keyboard.press("Enter")
                    print("[*] Image sent!")
                    await asyncio.sleep(random.uniform(4, 7))
                    
                    # === STEP 4: Now send text as standalone message ===
                    msg_box = await page.query_selector(msg_box_selector)
                    if msg_box:
                        await msg_box.click()
                        await asyncio.sleep(random.uniform(0.5, 1))
                    
                    # Native cross-platform insert instead of clipboard
                    await page.keyboard.insert_text(message)
                    await asyncio.sleep(random.uniform(1, 2))
                    await page.keyboard.press("Enter")
                    
                else:
                    # === TEXT-ONLY ===
                    msg_box = await page.query_selector(msg_box_selector)
                    await msg_box.click()
                    await asyncio.sleep(random.uniform(0.5, 1))
                    
                    # Native cross-platform insert instead of clipboard
                    await page.keyboard.insert_text(message)
                    await asyncio.sleep(random.uniform(1, 2))
                    await page.keyboard.press("Enter")
                    
                print(f"[+] Message dispatched to '{group_name}'")

                # Record the message for rate limiting
                _record_message(group_name)
                hr, _ = get_rate_limit_status(group_name)
                limit = _get_hourly_limit(group_name)
                print(f"[RATE] Messages sent: {hr}/{limit} this hour for this group")

                # Wait for message to actually send before closing
                await asyncio.sleep(random.uniform(5, 8))
                
            except Exception as e:
                print(f"[-] Failed to send Playwright message: {e}")
                print(f"[!] Applying error cooldown ({SESSION_COOLDOWN_ON_ERROR}s) to protect session...")
                await asyncio.sleep(SESSION_COOLDOWN_ON_ERROR)
                raise e
            finally:
                await browser.close()
    finally:
        try:
            if os.name == 'nt':
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except (IOError, OSError):
            pass
        lock_fd.close()

    # === POST-SEND COOLDOWN (human-like gap before next message) ===
    cooldown = random.uniform(MIN_DELAY_BETWEEN_MSG, MAX_DELAY_BETWEEN_MSG)
    print(f"[*] Post-send cooldown: {cooldown:.1f}s before next message is allowed")
    await asyncio.sleep(cooldown)