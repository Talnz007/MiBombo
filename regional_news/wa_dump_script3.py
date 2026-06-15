import asyncio
import os
from playwright.async_api import async_playwright

async def inspect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "whatsapp_session")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir, headless=True,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await browser.new_page()
        try:
            await page.goto("https://web.whatsapp.com/", timeout=60000)
            # Try multiple selectors for search
            try:
                await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=15000)
            except:
                await page.wait_for_selector('[aria-label="Search input textbox"]', timeout=15000)
            
            search_box = await page.query_selector('div[contenteditable="true"][data-tab="3"]') or await page.query_selector('[aria-label="Search input textbox"]')
            await search_box.fill("Automated news")
            await asyncio.sleep(2)
            await page.wait_for_selector('span[title="Automated news"]', timeout=10000)
            await page.click('span[title="Automated news"]')
            await asyncio.sleep(2)

            # Click attach
            attach_sel = 'button[aria-label="Attach"], span[data-icon="plus-rounded"]'
            await page.wait_for_selector(attach_sel, timeout=20000)
            await page.click(attach_sel)
            await asyncio.sleep(2)

            # Take screenshot
            await page.screenshot(path="wa_attach_menu.png")
            print("Screenshot saved to wa_attach_menu.png")

            # Dump all input[type=file]
            inputs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input[type="file"]')).map(e => ({
                    accept: e.getAttribute('accept'),
                    id: e.id,
                    parentAriaLabel: e.parentElement ? e.parentElement.getAttribute('aria-label') : null
                }));
            }''')
            print("File inputs found:", len(inputs))
            for inp in inputs:
                print(f"  accept={inp['accept']}, id={inp['id']}, parentAriaLabel={inp['parentAriaLabel']}")

            # Also look for all inputs
            all_inputs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input')).map(e => ({
                    type: e.type,
                    accept: e.getAttribute('accept'),
                    ariaHidden: e.getAttribute('aria-hidden'),
                    className: e.className ? e.className.substring(0, 60) : ''
                }));
            }''')
            print("\\nAll inputs:")
            for inp in all_inputs:
                print(f"  {inp}")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
