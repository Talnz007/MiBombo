import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_reporter import generate_osint_report, parse_category
from whatsapp_dispatcher import send_whatsapp_pw, SHARED_SESSION_DIR

async def send_to_phone(phone: str, message: str):
    from playwright.async_api import async_playwright
    import random
    
    print(f"[*] Connecting to WhatsApp for phone: {phone}")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=SHARED_SESSION_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await browser.new_page()
        # Direct URL to jump directly to a chat without search UI issues for unsaved numbers
        await page.goto(f"https://web.whatsapp.com/send?phone={phone}", timeout=60000)
        
        # Wait for chat input box
        msg_box_selector = 'div[role="textbox"][aria-label^="Type a message"]'
        # Also handle placeholder variations
        try:
            await page.wait_for_selector(msg_box_selector, timeout=30000)
            await asyncio.sleep(5) # wait to settle
            
            # Use clipboard to preserve newlines cleanly
            await page.evaluate('navigator.clipboard.writeText(arguments[0])', message)
            await page.focus(msg_box_selector)
            await page.keyboard.press('Control+v')
            await asyncio.sleep(2)
            await page.keyboard.press("Enter")
            print(f"[+] Successfully sent message to {phone}!")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[-] Failed to send message to {phone}: {e}")
        finally:
            await browser.close()

async def main():
    item = {
        "platform": "Twitter",
        "account": "TKCkhyber",
        "date": "2026-04-23T10:44:00.000Z",
        "url": "https://x.com/TKCkhyber/status/2047265222789152827",
        "text": "If the Afghan Taliban have arrested any extremist, then they should bring it to Pakistan's notice that they have arrested this person; if cases are running against them in the courts, then Pakistan's ..."
    }
    
    print("==========================================")
    print("   TESTING GROK GREENLET FIX + WHATSAPP   ")
    print("==========================================")
    
    print("[*] Generating report via Grok...")
    
    import multiprocessing
    import concurrent.futures
    import functools
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(pool,
            functools.partial(generate_osint_report, item, None)
        )
    
    print("\n--- GENERATED REPORT ---")
    print(report)
    print("------------------------\n")
    
    if "[OSINT AI ERROR]" in report or "RAW OSINT Update" in report:
        print("[-] Fallback triggered! The greenlet error or Grok block is still happening.")
        return
        
    category, clean_report = parse_category(report)
    print(f"[*] Category parsed: {category}")
    print(f"[*] Clean report size: {len(clean_report)} chars")
    
    target_number = "923205622747"
    await send_to_phone(target_number, clean_report)

if __name__ == "__main__":
    asyncio.run(main())