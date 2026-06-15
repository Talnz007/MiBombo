import asyncio
import os
from playwright.async_api import async_playwright

async def inspect_wa():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "whatsapp_session")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await browser.new_page()
        try:
            print("Going to WhatsApp...")
            await page.goto("https://web.whatsapp.com/", timeout=60000)
            print("Waiting for search box...")
            await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=30000)
            
            search_box = await page.query_selector('div[contenteditable="true"][data-tab="3"]')
            await search_box.fill("Automated news")
            await asyncio.sleep(2)
            
            chat_title_selector = f'span[title="Automated news"]'
            await page.wait_for_selector(chat_title_selector, timeout=10000)
            await page.click(chat_title_selector)
            await asyncio.sleep(2)
            
            print("Extracting buttons aria labels...")
            labels = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label') + ' - Tag: ' + e.tagName);
            }''')
            for l in labels:
                print(l)
                
            print("Extracting data-icons...")
            icons = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('[data-icon]')).map(e => e.getAttribute('data-icon') + ' - Tag: ' + e.tagName);
            }''')
            for i in icons:
                print(i)
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()
        
if __name__ == "__main__":
    asyncio.run(inspect_wa())
