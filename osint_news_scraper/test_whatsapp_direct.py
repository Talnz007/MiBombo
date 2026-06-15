import asyncio
import os
import sys
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from whatsapp_dispatcher import SHARED_SESSION_DIR

async def send_direct(phone, message):
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
            print("[*] Waiting for chat UI to load...")
            await page.wait_for_selector(msg_box_selector, timeout=60000)
            await asyncio.sleep(5)
            
            # Type message
            await page.evaluate('(msg) => navigator.clipboard.writeText(msg)', message)
            await page.focus(msg_box_selector)
            await page.keyboard.press('Control+v')
            await asyncio.sleep(2)
            await page.keyboard.press("Enter")
            print(f"[+] Successfully sent direct test message to {phone}!")
            await asyncio.sleep(6) # ensure it gets sent before closing
        except Exception as e:
            print(f"[-] Failed to send message: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    msg = """*Aoa, sir!* 🤖

This is an automated test message from the OSINT News Scraper.

The Greenlet execution blocker has been resolved, and direct phone number messaging integration was successful.

*Regards*"""
    
    asyncio.run(send_direct("923205622747", msg))