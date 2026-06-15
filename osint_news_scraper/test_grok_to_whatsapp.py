import asyncio
import os
import sys
import json
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_reporter import generate_osint_report, parse_category
from whatsapp_dispatcher import SHARED_SESSION_DIR

def generate_report_sync(item, img_path):
    """Sync wrapper to run in ProcessPoolExecutor"""
    return generate_osint_report(item, img_path)

async def send_to_phone(phone, message):
    """Send message via WhatsApp Web to a phone number"""
    print(f"[*] Connecting to WhatsApp for phone: {phone}")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=SHARED_SESSION_DIR,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            page = await browser.new_page()
            await page.goto(f"https://web.whatsapp.com/send?phone={phone}", timeout=60000)
            
            msg_box_selector = 'div[role="textbox"][aria-label^="Type a message"]'
            print(f"[*] Waiting for chat UI to load... (timeout: 60s)")
            await page.wait_for_selector(msg_box_selector, timeout=60000)
            await asyncio.sleep(3)
            
            # Use clipboard to preserve formatting
            await page.evaluate('(msg) => navigator.clipboard.writeText(msg)', message)
            await page.focus(msg_box_selector)
            await page.keyboard.press('Control+v')
            await asyncio.sleep(2)
            await page.keyboard.press("Enter")
            print(f"[+] Successfully sent message to {phone}!")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[-] Failed to send message: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

async def main():
    print("=" * 60)
    print("   GROK REPORT → DIRECT WHATSAPP TEST")
    print("=" * 60)
    
    # Sample news item (you can replace with real scraper data)
    item = {
        "platform": "Twitter",
        "account": "TKCkhyber",
        "date": "2026-04-23T10:44:00.000Z",
        "url": "https://x.com/TKCkhyber/status/2047265222789152827",
        "text": "If the Afghan Taliban have arrested any extremist, then they should bring it to Pakistan's notice that they have arrested this person; if cases are running against them in the courts, then Pakistan's government should seek details from them.",
        "screenshot": None
    }
    
    print(f"\n[*] Processing news from @{item['account']}...")
    print(f"    URL: {item['url']}")
    print(f"    Text: {item['text'][:80]}...\n")
    
    # Generate report in separate process to avoid greenlet/asyncio collision
    print("[*] Generating Grok report (running in isolated ProcessPoolExecutor)...")
    with ProcessPoolExecutor(max_workers=1) as executor:
        loop = asyncio.get_event_loop()
        try:
            report = await loop.run_in_executor(
                executor,
                partial(generate_report_sync, item, None)
            )
        except Exception as e:
            print(f"[-] Error generating report: {e}")
            return
    
    if not report or len(report) < 50:
        print("[-] Report generation failed or returned empty!")
        return
    
    print(f"\n[+] Report generated successfully ({len(report)} chars)")
    print("\n" + "="*60)
    print("GENERATED REPORT:")
    print("="*60)
    print(report)
    print("="*60 + "\n")
    
    # Check category
    category, clean_report = parse_category(report)
    print(f"[*] Category: {category}")
    
    # Send to phone
    phone = "923205622747"
    print(f"\n[*] Sending to WhatsApp: +{phone}")
    await send_to_phone(phone, clean_report)
    
    print("\n[+] Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
