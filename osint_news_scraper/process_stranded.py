import os
import json
import asyncio
from main import dispatch_item, cleanup_media

async def process_stranded_media():
    log_file = os.path.join("output", "osint_latest_news.json")
    media_dir = os.path.join("output", "media")
    
    if not os.path.exists(log_file) or not os.path.exists(media_dir):
        print("[!] Missing required directories/files.")
        return

    # List all stranded media files
    stranded_files = [os.path.join(media_dir, f) for f in os.listdir(media_dir) if f.endswith(('.png', '.jpg'))]
    print(f"[*] Found {len(stranded_files)} stranded media files.")
    
    if not stranded_files:
        return

    with open(log_file, "r", encoding="utf-8") as f:
        try:
            items = json.load(f)
        except:
            print("[-] Could not parse JSON array.")
            return

    # Find matching items in the JSON
    items_to_process = []
    
    stranded_basenames = [os.path.basename(f) for f in stranded_files]
    
    for item in items:
        # Check if the screenshot or any media in this item matches our stranded files and exists
        screenshot = item.get('screenshot')
        media_list = item.get('media', [])
        
        has_stranded_media = False
        if screenshot and os.path.basename(screenshot) in stranded_basenames:
            # Reattach the absolute/relative correct path needed to find the file
            has_stranded_media = True
            
        for m in media_list:
            if m and os.path.basename(m) in stranded_basenames:
                has_stranded_media = True
                
        if has_stranded_media:
            # Prevent duplicates
            if not any(i.get('url') == item.get('url') for i in items_to_process):
                items_to_process.append(item)

    print(f"[*] Associated {len(items_to_process)} JSON items with the stranded media.")

    success_count = 0
    for i, item in enumerate(items_to_process):
        print(f"\n--- PROCESSING STRANDED MEDIA ITEM {i+1}/{len(items_to_process)} ---")
        try:
            await dispatch_item(item)
            success_count += 1
            await asyncio.sleep(8)
        except Exception as e:
            print(f"[!] Failed to process item: {e}")

    print(f"\n[+] Finished processing stranded media. Successfully sent {success_count}/{len(items_to_process)}")

if __name__ == "__main__":
    asyncio.run(process_stranded_media())
