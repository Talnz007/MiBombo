import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    
    # Load cookies
    import pickle
    with open('/home/talnz/PythonProjects/automatingwork/cookies/twitter_cookies.pkl', 'rb') as f:
        cookies = pickle.load(f)
    context.add_cookies([{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]} for c in cookies])
    
    page = context.new_page()
    page.goto('https://x.com/i/grok')
    time.sleep(10)
    
    textareas = page.locator('textarea')
    count = textareas.count()
    print(f"Total textareas: {count}")
    
    for i in range(count):
        loc = textareas.nth(i)
        is_visible = loc.is_visible()
        placeholder = loc.get_attribute('placeholder')
        aria_label = loc.get_attribute('aria-label')
        cls = loc.get_attribute('class')
        print(f"Textarea {i}: visible={is_visible}, placeholder='{placeholder}', aria-label='{aria_label}', class='{cls}'")

    browser.close()
