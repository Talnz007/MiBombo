import os
from playwright.sync_api import sync_playwright

# Use the shared session at project root
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_SESSION_DIR = os.path.join(WORKSPACE_DIR, "whatsapp_session")

def open_session():
    print(f"[*] Using shared session at: {SHARED_SESSION_DIR}")
    if not os.path.exists(SHARED_SESSION_DIR):
        print(f"[!] Session dir not found: {SHARED_SESSION_DIR}")
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SHARED_SESSION_DIR,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Remove webdriver flag
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page.goto("https://web.whatsapp.com")
        
        # Keeps the browser open until you press Enter in the terminal
        input("Session open. Press Enter to close and save state...\n")
        context.close()

if __name__ == "__main__":
    open_session()
