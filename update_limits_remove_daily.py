import json
import os

files = [
    "/home/talnz/PythonProjects/automatingwork/osint_news_scraper/whatsapp_dispatcher.py",
    "/home/talnz/PythonProjects/automatingwork/regional_news/whatsapp_dispatcher.py"
]

REPLACE_OLD_CONFIG = """MAX_MESSAGES_PER_HOUR_DEFAULT = 25  # Fallback
MAX_MESSAGES_PER_DAY  = 80      # Hard cap per day (across all groups combined)
MIN_DELAY_BETWEEN_MSG = 10      # Minimum seconds between messages"""

REPLACE_NEW_CONFIG = """MAX_MESSAGES_PER_HOUR_DEFAULT = 25  # Fallback
# Daily cap removed to prevent missing critical messages
MIN_DELAY_BETWEEN_MSG = 10      # Minimum seconds between messages"""

FUNCTIONS_OLD = """def _check_rate_limit(group_name: str = "default"):
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
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")"""

FUNCTIONS_NEW = """def _check_rate_limit(group_name: str = "default"):
    \"\"\"
    Returns (allowed: bool, wait_seconds: float).
    \"\"\"
    data = _load_rate_data()
    now = datetime.now()
    
    # Prune messages older than 1 hour across all categories to keep file size small
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    for cat in list(data["messages"].keys()):
        data["messages"][cat] = [ts for ts in data["messages"][cat] if ts > cutoff_hour]

    # Count messages for specifically this group in the last hour
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")"""


FUNCTIONS_OLD2 = """def get_rate_limit_status(group_name: str = "default"):
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

FUNCTIONS_NEW2 = """def get_rate_limit_status(group_name: str = "default"):
    \"\"\"Public helper: returns (msgs_last_hour_for_group, 0) for monitoring.\"\"\"
    data = _load_rate_data()
    now = datetime.now()
    cutoff_hour = (now - timedelta(hours=1)).isoformat()
    
    cat_id = "global" if ("global" in group_name.lower() or "automated" in group_name.lower()) else ("regional" if "regional" in group_name.lower() else "default")
    group_msgs = data["messages"].get(cat_id, [])
    
    msgs_hour = len([ts for ts in group_msgs if ts > cutoff_hour])
        
    return msgs_hour, 0"""


PRINT_OLD = """                # Record the message for rate limiting
                _record_message(group_name)
                hr, day = get_rate_limit_status(group_name)
                limit = _get_hourly_limit(group_name)
                print(f"[RATE] Messages sent: {hr}/{limit} this hour for this group, "
                      f"{day}/{MAX_MESSAGES_PER_DAY} today globally")"""

PRINT_NEW = """                # Record the message for rate limiting
                _record_message(group_name)
                hr, _ = get_rate_limit_status(group_name)
                limit = _get_hourly_limit(group_name)
                print(f"[RATE] Messages sent: {hr}/{limit} this hour for this group")"""


for f_path in files:
    with open(f_path, 'r') as f:
        content = f.read()
    
    content = content.replace(REPLACE_OLD_CONFIG, REPLACE_NEW_CONFIG)
    content = content.replace(FUNCTIONS_OLD, FUNCTIONS_NEW)
    content = content.replace(FUNCTIONS_OLD2, FUNCTIONS_NEW2)
    content = content.replace(PRINT_OLD, PRINT_NEW)
    
    with open(f_path, 'w') as f:
        f.write(content)

print("DONE")
