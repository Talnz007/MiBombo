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
    """
    message = clean_osint_report(message)

    # === RATE LIMIT CHECK ===
    allowed, wait_time = _check_rate_limit(group_name)
    if not allowed:
        print(f"[RATE LIMIT] Skipping message to '{group_name}' — rate limit active.")
        return 

    # === SESSION VALIDATION ===
    if not os.path.exists(SHARED_SESSION_DIR):
        print(f"[!] CRITICAL: Shared session directory not found at {SHARED_SESSION_DIR}")
        raise FileNotFoundError(f"WhatsApp session not found: {SHARED_SESSION_DIR}")

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
                ]
            )
            
            page = await browser.new_page()

            try:
                # Detect if group_name is actually a phone number
                is_phone = re.match(r'^\+?\d{10,15}$', group_name.replace(" ", "").replace("-", ""))
                
                if is_phone:
                    phone_clean = re.sub(r'\D', '', group_name)
                    print(f"[*] Opening direct WhatsApp link for phone: {phone_clean}")
                    await page.goto(f"https://web.whatsapp.com/send?phone={phone_clean}", timeout=60000)
                else:
                    print(f"[*] Opening WhatsApp Web to find '{group_name}'...")
                    await page.goto("https://web.whatsapp.com/", timeout=60000)
                
                # === WAIT FOR CHAT LOAD ===
                msg_box_selector = 'div[role="textbox"][aria-label^="Type a message"]'
                search_selector = 'input[aria-label="Search or start a new chat"]'

                try:
                    await page.wait_for_selector(f'{msg_box_selector}, {search_selector}', timeout=45000)
                except:
                    print("[!] Session load timeout. Waiting 60s for QR/Login...")
                    await page.wait_for_selector(f'{msg_box_selector}, {search_selector}', timeout=60000)

                if not is_phone:
                    # HUMAN-LIKE SEARCH FOR GROUPS
                    await asyncio.sleep(random.uniform(1, 3))
                    await page.fill(search_selector, group_name)
                    await asyncio.sleep(random.uniform(2, 4))
                    chat_title = f'span[title="{group_name}"]'
                    await page.wait_for_selector(chat_title, timeout=10000)
                    await page.click(chat_title)
                    await asyncio.sleep(random.uniform(2, 4))
                else:
                    # For direct phone links, just wait for the box to appear
                    await page.wait_for_selector(msg_box_selector, timeout=60000)
                    await asyncio.sleep(random.uniform(3, 5))

                # === SENDING LOGIC ===
                has_image = image_path and os.path.exists(image_path) and "blank_msg.png" not in image_path
                
                if has_image:
                    attach_sel = 'button[aria-label="Attach"], span[data-icon="plus-rounded"]'
                    await page.click(attach_sel)
                    await asyncio.sleep(1)
                    async with page.expect_file_chooser() as fc_info:
                        await page.click('text="Photos & videos"')
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(image_path)
                    await asyncio.sleep(random.uniform(3, 5))
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(random.uniform(3, 5))
                    
                # Send text
                await page.click(msg_box_selector)
                await page.keyboard.insert_text(message)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                
                print(f"[+] Message dispatched to '{group_name}'")
                _record_message(group_name)
                await asyncio.sleep(random.uniform(5, 8))
                
            except Exception as e:
                print(f"[-] Failed to send message: {e}")
                raise e
            finally:
                await browser.close()
    finally:
        try:
            if os.name == 'nt':
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except:
            pass
        lock_fd.close()

    cooldown = random.uniform(MIN_DELAY_BETWEEN_MSG, MAX_DELAY_BETWEEN_MSG)
    await asyncio.sleep(cooldown)