import json
import os

files = [
    "/home/talnz/PythonProjects/automatingwork/osint_news_scraper/whatsapp_dispatcher.py",
    "/home/talnz/PythonProjects/automatingwork/regional_news/whatsapp_dispatcher.py"
]

REPLACE_OLD = """# ──────────────────── SAFETY CONFIGURATION ────────────────────
# These limits protect the WhatsApp account from being flagged
MAX_MESSAGES_PER_HOUR = 25      # Hard cap per hour
MAX_MESSAGES_PER_DAY  = 80      # Hard cap per day (across all groups)
MIN_DELAY_BETWEEN_MSG = 10      # Minimum seconds between messages
MAX_DELAY_BETWEEN_MSG = 25      # Maximum seconds between messages (randomized)"""

REPLACE_NEW = """# ──────────────────── SAFETY CONFIGURATION ────────────────────
# These limits protect the WhatsApp account from being flagged
MAX_MESSAGES_PER_HOUR_GLOBAL = 5   # Hourly cap for Global/Automated news
MAX_MESSAGES_PER_HOUR_REGIONAL = 20 # Hourly cap for Regional news
MAX_MESSAGES_PER_HOUR_DEFAULT = 25  # Fallback
MAX_MESSAGES_PER_DAY  = 80      # Hard cap per day (across all groups combined)
MIN_DELAY_BETWEEN_MSG = 10      # Minimum seconds between messages
MAX_DELAY_BETWEEN_MSG = 25      # Maximum seconds between messages (randomized)"""

FUNCTIONS_OLD = """def _load_rate_data():
    \"\"\"Load rate limiting data from disk.\"\"\"
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"messages": []}

def _save_rate_data(data):
    \"\"\"Persist rate limiting data to disk.\"\"\"
    try:
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"[!] Could not save rate limit data: {e}")

def _check_rate_limit():
    \"\"\"
    Returns (allowed: bool, wait_seconds: float).
    If not allowed, wait_seconds tells the caller how long to wait.
    \"\"\"
    data = _load_rate_data()
    now = datetime.now()
    now_str = now.isoformat()

    # Prune messages older than 24 hours
    cutoff_day = (now - timedelta(hours=24)).isoformat()
    data["messages"] = [ts for ts in data["messages"] if ts > cutoff_day]

    # Count messages in the last hour
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    msgs_last_hour = [ts for ts in data["messages"] if ts > cutoff_hour]
    msgs_last_day = data["messages"]

    if len(msgs_last_day) >= MAX_MESSAGES_PER_DAY:
        # Find the oldest message and compute when it'll expire
        oldest = min(msgs_last_day)
        expire_at = datetime.fromisoformat(oldest) + timedelta(hours=24)
        wait = (expire_at - now).total_seconds()
        print(f"[RATE LIMIT] Daily cap reached ({len(msgs_last_day)}/{MAX_MESSAGES_PER_DAY}). "
              f"Must wait {wait/60:.0f} minutes.")
        return False, max(wait, 60)

    if len(msgs_last_hour) >= MAX_MESSAGES_PER_HOUR:
        oldest_hour = min(msgs_last_hour)
        expire_at = datetime.fromisoformat(oldest_hour) + timedelta(hours=1)
        wait = (expire_at - now).total_seconds()
        print(f"[RATE LIMIT] Hourly cap reached ({len(msgs_last_hour)}/{MAX_MESSAGES_PER_HOUR}). "
              f"Must wait {wait/60:.1f} minutes.")
        return False, max(wait, 30)

    return True, 0

def _record_message():
    \"\"\"Record that a message was sent (for rate limiting).\"\"\"
    data = _load_rate_data()
    data["messages"].append(datetime.now().isoformat())
    _save_rate_data(data)

def get_rate_limit_status():
    \"\"\"Public helper: returns (msgs_last_hour, msgs_last_day) for monitoring.\"\"\"
    data = _load_rate_data()
    now = datetime.now()
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    cutoff_day = (now - timedelta(hours=24)).isoformat()
    msgs_hour = len([ts for ts in data["messages"] if ts > cutoff_hour])
    msgs_day = len([ts for ts in data["messages"] if ts > cutoff_day])
    return msgs_hour, msgs_day"""

FUNCTIONS_NEW = """def _get_hourly_limit(group_name: str) -> int:
    name = group_name.lower()
    if "global" in name or "automated news" in name:
        return MAX_MESSAGES_PER_HOUR_GLOBAL
    elif "regional" in name:
        return MAX_MESSAGES_PER_HOUR_REGIONAL
    return MAX_MESSAGES_PER_HOUR_DEFAULT

def _load_rate_data():
    \"\"\"Load rate limiting data from disk.\"\"\"
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
    \"\"\"Persist rate limiting data to disk.\"\"\"
    try:
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"[!] Could not save rate limit data: {e}")

def _check_rate_limit(group_name: str = "default"):
    \"\"\"
    Returns (allowed: bool, wait_seconds: float).
    \"\"\"
    data = _load_rate_data()
    now = datetime.now()
    
    # Prune messages older than 24 hours across all categories
    cutoff_day = (now - timedelta(hours=24)).isoformat()
    all_day_msgs = []
    for cat in list(data["messages"].keys()):
        data["messages"][cat] = [ts for ts in data["messages"][cat] if ts > cutoff_day]
        all_day_msgs.extend(data["messages"][cat])

    if len(all_day_msgs) >= MAX_MESSAGES_PER_DAY:
        oldest = min(all_day_msgs)
        expire_at = datetime.fromisoformat(oldest) + timedelta(hours=24)
        wait = (expire_at - now).total_seconds()
        print(f"[RATE LIMIT] Global Daily cap reached ({len(all_day_msgs)}/{MAX_MESSAGES_PER_DAY}). "
              f"Must wait {wait/60:.0f} minutes.")
        return False, max(wait, 60)

    # Count messages for specifically this group in the last hour
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
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
    \"\"\"Record that a message was sent (for rate limiting).\"\"\"
    data = _load_rate_data()
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    
    if cat_id not in data["messages"]:
        data["messages"][cat_id] = []
        
    data["messages"][cat_id].append(datetime.now().isoformat())
    _save_rate_data(data)

def get_rate_limit_status(group_name: str = "default"):
    \"\"\"Public helper: returns (msgs_last_hour_for_group, total_msgs_last_day) for monitoring.\"\"\"
    data = _load_rate_data()
    now = datetime.now()
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    cutoff_day = (now - timedelta(hours=24)).isoformat()
    
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    group_msgs = data["messages"].get(cat_id, [])
    
    msgs_hour = len([ts for ts in group_msgs if ts > cutoff_hour])
    
    total_day = 0
    for cat, msgs in data["messages"].items():
        total_day += len([ts for ts in msgs if ts > cutoff_day])
        
    return msgs_hour, total_day"""

DISPATCHER_OLD = """    # === RATE LIMIT CHECK ===
    allowed, wait_time = _check_rate_limit()"""

DISPATCHER_NEW = """    # === RATE LIMIT CHECK ===
    allowed, wait_time = _check_rate_limit(group_name)"""

REC_NEW = """                # Record the message for rate limiting
                _record_message(group_name)
                hr, day = get_rate_limit_status(group_name)
                limit = _get_hourly_limit(group_name)
                print(f"[RATE] Messages sent: {hr}/{limit} this hour for this group, "
                      f"{day}/{MAX_MESSAGES_PER_DAY} today globally")"""

REC_OLD = """                # Record the message for rate limiting
                _record_message()
                hr, day = get_rate_limit_status()
                print(f"[RATE] Messages sent: {hr}/{MAX_MESSAGES_PER_HOUR} this hour, "
                      f"{day}/{MAX_MESSAGES_PER_DAY} today")"""


for f_path in files:
    with open(f_path, 'r') as f:
        content = f.read()
    
    content = content.replace(REPLACE_OLD, REPLACE_NEW)
    content = content.replace(FUNCTIONS_OLD, FUNCTIONS_NEW)
    content = content.replace(DISPATCHER_OLD, DISPATCHER_NEW)
    content = content.replace(REC_OLD, REC_NEW)
    
    with open(f_path, 'w') as f:
        f.write(content)
        
print("DONE")

