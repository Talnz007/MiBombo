import os
import json
import asyncio
from main import dispatch_item

async def process_backlog():
    log_file = os.path.join("output", "osint_latest_news.json")
    if not os.path.exists(log_file):
        print("[!] No backlog found.")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        try:
            items = json.load(f)
        except:
            print("[-] Could not parse JSON array.")
            return

    print(f"[*] Found {len(items)} items in backlog.")
    
    # Just process the last 15 items to be safe it's not the whole history
    backlog = items[-15:]
    print(f"[*] Processing the last {len(backlog)} items...")

    success_count = 0
    for i, item in enumerate(backlog):
        print(f"\n--- PROCESSING BACKLOG ITEM {i+1}/{len(backlog)} ---")
        try:
            await dispatch_item(item)
            success_count += 1
            await asyncio.sleep(8)
        except Exception as e:
            print(f"[!] Failed to process item: {e}")

    print(f"\n[+] Finished processing backlog. successfully sent {success_count}/{len(backlog)}")

if __name__ == "__main__":
    asyncio.run(process_backlog())
