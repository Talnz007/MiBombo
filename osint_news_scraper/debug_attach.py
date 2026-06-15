import asyncio
import os
from playwright.async_api import async_playwright

async def debug():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "whatsapp_session")
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir, headless=False,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await browser.new_page()
        try:
            await page.goto("https://web.whatsapp.com/", timeout=60000)
            search_selector = 'div[contenteditable="true"][data-tab="3"]'
            await page.wait_for_selector(search_selector, timeout=30000)
            search_box = await page.query_selector(search_selector)
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

            # Screenshot the attach menu
            await page.screenshot(path="debug_attach_menu.png")
            print("Saved debug_attach_menu.png")

            # Dump everything visible in the menu
            menu_items = await page.evaluate('''() => {
                const items = [];
                // Look for all buttons and interactive elements
                document.querySelectorAll('button, [role="button"], li, [role="application"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        items.push({
                            tag: el.tagName,
                            ariaLabel: el.getAttribute('aria-label'),
                            text: el.textContent.trim().substring(0, 50),
                            dataIcon: el.querySelector('[data-icon]') ? el.querySelector('[data-icon]').getAttribute('data-icon') : null,
                            hasFileInput: el.querySelector('input[type="file"]') ? true : false,
                            x: Math.round(rect.x),
                            y: Math.round(rect.y)
                        });
                    }
                });
                return items.filter(i => i.ariaLabel || i.dataIcon || i.hasFileInput);
            }''')
            print("\n=== VISIBLE MENU ITEMS ===")
            for item in menu_items:
                print(f"  {item}")

            # Now specifically find file inputs and their parent structure
            print("\n=== FILE INPUTS ===")
            file_info = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input[type="file"]')).map(el => {
                    let parent = el.parentElement;
                    let ancestors = [];
                    for (let i = 0; i < 5 && parent; i++) {
                        ancestors.push({
                            tag: parent.tagName,
                            ariaLabel: parent.getAttribute('aria-label'),
                            role: parent.getAttribute('role'),
                            dataIcon: parent.querySelector(':scope > [data-icon]') ? parent.querySelector(':scope > [data-icon]').getAttribute('data-icon') : null
                        });
                        parent = parent.parentElement;
                    }
                    return {
                        accept: el.getAttribute('accept'),
                        multiple: el.multiple,
                        hidden: el.hidden,
                        display: getComputedStyle(el).display,
                        ancestors: ancestors
                    };
                });
            }''')
            for fi in file_info:
                print(f"  {fi}")

            # Try clicking "Photos & Videos" button
            print("\n=== TRYING TO CLICK Photos & Videos ===")
            photos_btn = await page.query_selector('button[aria-label="Photos & videos"]')
            if photos_btn:
                print("Found button[aria-label='Photos & videos']!")
            else:
                # Try other selectors
                for sel in ['span[data-icon="media-refreshed"]', 'span[data-icon="attach-image"]', 
                           'button:has-text("Photos")', 'li:has-text("Photos")']:
                    el = await page.query_selector(sel)
                    if el:
                        print(f"Found: {sel}")
                        break
                    else:
                        print(f"NOT found: {sel}")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
