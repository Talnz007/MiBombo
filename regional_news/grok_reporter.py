import os
import time
import pickle
from playwright.sync_api import sync_playwright
from config import TWITTER_COOKIES_PATH
import glob
import markdownify
import re

import sys
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)
from shared_cookie_manager import get_current_cookie_file, rotate_cookie

def load_cookies(context):
    cookie_path = get_current_cookie_file()
    print(f"[*] Loading cookies from {cookie_path}")
    try:
        with open(cookie_path, "rb") as f:
            cookies = pickle.load(f)
        pw_cookies = []
        for c in cookies:
            same_site = c.get("sameSite", "Lax")
            if isinstance(same_site, str):
                if same_site.lower() == "no_restriction":
                    same_site = "None"
                else:
                    same_site = same_site.capitalize()
                if same_site not in ["Strict", "Lax", "None"]:
                    same_site = "Lax"
            else:
                same_site = "Lax"
                
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": c.get("expiry", c.get("expirationDate", -1)),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": same_site,
            })
        context.add_cookies(pw_cookies)
        return True
    except Exception as e:
        print(f"[!] Error loading Twitter cookies: {e}")
        return False

def _query_grok_single(prompt: str, timeout_seconds=300) -> str:
    """
    Spins up Playwright, navigates to Grok, submits the prompt, 
    and extracts the response.
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-http-cache",
                "--disk-cache-size=1",
                "--media-cache-size=1",
                "--disable-gpu", 
                "--disable-software-rasterizer", 
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            permissions=["clipboard-read", "clipboard-write"]
        )
        
        if not load_cookies(context):
            browser.close()
            return ""
            
        page = context.new_page()
        
        loaded = False
        textarea = None
        for attempt in range(5):
            try:
                print(f"[*] Navigating to Grok (Attempt {attempt+1}/5)...")
                # Even larger timeout for slow internet + wait_until="commit" to be faster
                try:
                    page.goto("https://x.com/i/grok", timeout=120000, wait_until="commit")
                except Exception as e:
                    print(f"[-] Page.goto timed out or failed: {str(e)}. Checking if content exists anyway...")
                
                # Check for textarea FIRST. If it's there, we are good regardless of warnings.
                try:
                    textarea = page.wait_for_selector('textarea', timeout=30000)
                except:
                    textarea = None

                if textarea:
                    print("[+] Grok UI loaded successfully (textarea found).")
                    loaded = True
                    break

                # If no textarea, check for hard service errors
                body_text = page.locator("body").text_content()
                if "Service Unavailable" in body_text or "Something went wrong" in body_text or "Experiencing issues with Grok" in body_text:
                    if not textarea: # Only reload if UI isn't there
                        print("[!] Grok service issue detected and UI missing. Doing hard reload...")
                        page.keyboard.press("Control+Shift+R")
                        time.sleep(5)
                        continue

            except Exception as e:
                print(f"[-] Attempt {attempt+1} failed: {str(e)}. Triggering hard reload...")
                try:
                    page.keyboard.press("Control+Shift+R")
                    time.sleep(5)
                except:
                    pass
                continue
                
        if not loaded or not textarea:
            print("[!] Could not load Grok after 5 attempts. Checking if rotation is needed.")
            # If we see "Service Unavailable" consistently, we return a specific signal
            if "Service Unavailable" in page.locator("body").text_content():
                browser.close()
                return "SERVICE_UNAVAILABLE"
            browser.close()
            return ""
            
        time.sleep(2)
        
        response_text = ""
        try:
                # Wait to ensure chat history loads, then count existing copy buttons
                time.sleep(4)
                try:
                    initial_md = page.locator("button[aria-label='Copy Markdown']").count()
                    initial_text = page.locator("button[aria-label='Copy text']").count()
                    initial_btns = initial_md + initial_text
                except:
                    initial_btns = 0
                
                print(f"[*] Initial Copy buttons on screen (history): {initial_btns}")

                # We need to fill the textarea, but Grok's text area can be buggy.
                # Use a locator instead of the stale ElementHandle to avoid "Element is not attached to the DOM"
                ta_loc = page.locator('textarea').first
                ta_loc.fill(prompt)
                time.sleep(2) # Give React time to register the large input
                ta_loc.press("Enter")
                
                # Check if it actually submitted by waiting for the textarea to clear
                # Or click the send button explicitly:
                try:
                    # The send button is usually an svg next to the textarea
                    page.locator('button[aria-label="Grok something"]').click(timeout=3000)
                except:
                    pass
                
                print("[+] Prompt submitted. Waiting for Grok to finish typing...")
                time.sleep(5) 
                
                # --- [ERROR DETECTION LOOP] ---
                for check in range(3):
                    body_text = page.locator("body").inner_text().lower()
                    if "something went wrong" in body_text or "please try again" in body_text:
                        print(f"[!] Detected Grok error (Check {check+1}). Hard reloading...")
                        page.reload(wait_until="domcontentloaded")
                        time.sleep(8)
                        # Re-find and re-submit
                        ta_loc = page.locator('textarea').first
                        if ta_loc.count() > 0:
                            ta_loc.fill(prompt)
                            ta_loc.press("Enter")
                            print("[+] Re-submitted prompt after hard reload.")
                            time.sleep(5)
                        else:
                            print("[-] Textarea missing after reload. Trying one more reload...")
                            page.goto("https://x.com/i/grok", wait_until="domcontentloaded")
                    else:
                        break # No error detected

                time.sleep(3) # Wait for UI to transition out of input mode
                
                # Check repeatedly if Grok has finished.
                start_time = time.time()
                
                while time.time() - start_time < timeout_seconds:
                    time.sleep(2)
                    
                    # Check if the number of copy buttons has increased (meaning the new message is done)
                    try:
                        current_md = page.locator("button[aria-label='Copy Markdown']").count()
                        current_text = page.locator("button[aria-label='Copy text']").count()
                        current_btns = current_md + current_text
                        
                        if current_btns > initial_btns:
                            print(f"[*] Copy button count increased ({initial_btns} -> {current_btns}). Generation complete.")
                            break
                    except Exception:
                        pass
                        
                    # Check for rate limits while waiting
                    try:
                        current_content = page.locator("body").text_content()
                        if "You've reached your limit" in current_content or "Upgrade to X Premium" in current_content:
                            print("[-] Rate limit detected while waiting for response.")
                            break
                    except Exception:
                        pass
                        
                page.screenshot(path="grok_debug_test.png", full_page=True)
                print("[+] Saved grok_debug_test.png for analysis")
                
                # ── PRIMARY: Click Copy icon, then click "Copy markdown" menu item ──
                print("[+] Grok finished typing. Trying Copy Markdown extraction...")
                try:
                    copy_icon = page.locator("button[aria-label='Copy text']").last
                    if copy_icon.count() > 0:
                        copy_icon.click()
                        time.sleep(0.5) # Wait for drop-down menu
                        
                        # Look for 'Copy markdown' in the menu (case insensitive)
                        md_option = page.locator("text=/Copy markdown/i")
                        if md_option.count() > 0:
                            print("[*] Found 'Copy markdown' menu option, clicking it.")
                            md_option.last.click()
                        else:
                            print("[!] 'Copy markdown' not found in menu, falling back to 'Copy text'")
                            txt_option = page.locator("text=/Copy text/i")
                            if txt_option.count() > 0:
                                txt_option.last.click()
                                
                        time.sleep(1)
                        clipboard_text = page.evaluate("navigator.clipboard.readText()")
                        if clipboard_text and len(clipboard_text.strip()) > 200:
                            response_text = clipboard_text.strip()
                            print(f"[+] Got response via clipboard ({len(response_text)} chars)")
                except Exception as e:
                    print(f"[-] Clipboard extraction failed: {e}")
                
                # ── FALLBACK: DOM parsing if clipboard didn't work ──
                if not response_text:
                    print("[+] Clipboard empty/failed. Extracting text directly from DOM container.")
                    final_text = ""
                    try:
                        # Grok's response is usually in a div with class 'markdown'
                        markdown_loc = page.locator(".markdown")
                        if markdown_loc.count() > 0:
                            # .markdown found — use BS4+markdownify (small HTML, fast)
                            raw_html = markdown_loc.last.inner_html()
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(raw_html, "html.parser")
                            for img in soup.find_all("img"):
                                alt = img.get("alt")
                                src = img.get("src", "")
                                if alt and ("twemoji" in src or "svg" in src or "emoji" in src.lower() or "abs.twimg.com" in src):
                                    img.replace_with(alt)
                            raw_html = str(soup)
                            final_text = markdownify.markdownify(raw_html, heading_style="ATX")
                            final_text = final_text.replace("\\[", "[").replace("\\]", "]")
                            final_text = final_text.replace("\\*", "*").replace("\\_", "_")
                            final_text = final_text.replace("\\#", "#").replace("\\-", "-")
                            final_text = final_text.replace("\\!", "!").replace("\\.", ".")
                            final_text = final_text.replace("\\(", "(").replace("\\)", ")")
                            final_text = final_text.replace("\\@", "@")
                            final_text = re.sub(r'\*{3,}', '**', final_text)
                            final_text = final_text.replace("🔶", "\n🔶").replace("🔹", "\n🔹")
                            final_text = re.sub(r'\*\*([^*]+)\*', r'**\1**', final_text)
                            final_text = re.sub(r'\*([^*]+)\*\*', r'**\1**', final_text)
                            response_text = final_text.strip()
                            print(f"[+] Got response via .markdown container ({len(response_text)} chars)")
                        else:
                            # .markdown NOT found — use fast inner_text() instead of slow BS4+markdownify on body
                            print("[-] .markdown not found. Using fast inner_text() extraction.")
                            final_text = page.locator("body").inner_text()
                            print(f"[+] Got body inner_text ({len(final_text)} chars). Parsing with markers...")
                    except Exception as e:
                        print(f"[-] Error extracting DOM: {e}")
                        try:
                            final_text = page.locator("body").inner_text()
                        except:
                            final_text = ""
                        
                    # If we still don't have response_text, parse from final_text using markers
                    if not response_text and final_text:
                        marker = "[END OF INPUT]"
                        after_prompt = ""
                        if marker in final_text:
                            after_prompt = final_text.split(marker)[-1].strip()
                        elif prompt in final_text:
                            after_prompt = final_text.split(prompt)[-1].strip()
                        else:
                            prompt_start = prompt.strip().splitlines()[0] if prompt.strip() else ""
                            if prompt_start and prompt_start in final_text:
                                after_prompt = final_text.split(prompt_start)[-1].strip()
                            else:
                                print("[-] Could not find prompt marker in final text! Slicing from end.")
                                lines = [line.strip() for line in final_text.splitlines() if line.strip()]
                                try:
                                    th_idx = -1
                                    for i, l in enumerate(lines):
                                        if "Think Harder" in l or "Make it " in l:
                                            th_idx = i
                                            break
                                    if th_idx != -1:
                                        response_text = "\n".join(lines[-20:th_idx])
                                    else:
                                        response_text = "\n".join(lines[-20:])
                                except:
                                    pass
                                
                        if after_prompt:
                            if "Make it " in after_prompt:
                                response_text = after_prompt.split("Make it ")[0].strip()
                            elif "Think Harder" in after_prompt:
                                response_text = after_prompt.split("Think Harder")[0].strip()
                            else:
                                response_text = after_prompt
        except Exception as e:
            print(f"[-] Error interacting with Grok: {e}")
            page.screenshot(path="grok_error_state.png", full_page=True)
            
        import threading, subprocess as _sp
        def _do_browser_close():
            try:
                for pg in context.pages:
                    try: pg.close()
                    except: pass
                browser.close()
            except: pass
        
        close_t = threading.Thread(target=_do_browser_close, daemon=True)
        close_t.start()
        close_t.join(timeout=10)
        if close_t.is_alive():
            print("[-] browser.close() timed out (10s). Force killing Playwright chrome...")
            try:
                result = _sp.run(
                    ['powershell', '-Command',
                     "Get-Process chrome -EA SilentlyContinue | Where-Object {$_.Path -like '*ms-playwright*'} | Stop-Process -Force"],
                    capture_output=True, timeout=10
                )
                print("[+] Force killed Playwright chrome processes.")
            except Exception as e:
                print(f"[-] Force kill failed: {e}")
        
    # Clean up the response (Remove Thought process and trailing UI text)
    if response_text:
        lines = response_text.splitlines()
        if len(lines) > 0 and lines[0].startswith("Thought for"):
            lines = lines[1:]
            
        # UI buttons like "Quick Answer" or suggested searches might be at the end.
        cleaned = "\n".join(lines)
        if "*Regards*" in cleaned:
            cleaned = cleaned.split("*Regards*")[0] + "*Regards*"
        elif "Regards" in cleaned:
            cleaned = cleaned.split("Regards")[0] + " Regards"
            
        response_text = cleaned.strip()
        
        # Collapse multiple asterisks caused by nested span parsing
        response_text = re.sub(r'\*{3,}', '**', response_text)
        
        # Fix emoji line spacing
        response_text = response_text.replace("\n\n🔶", "\n🔶").replace("🔶", "\n🔶")
        response_text = response_text.replace("\n\n🔹", "\n🔹").replace("🔹", "\n🔹")
        response_text = re.sub(r'\n{3,}', '\n\n', response_text)

    print(f"[+] Grok query finished. Output length: {len(response_text)}")
    
    # Check for rate limits explicitly in the raw response text
    if "You've reached your limit" in response_text or "Upgrade to X Premium" in response_text:
        return "RATE_LIMIT_REACHED"
        
    # Also check the page body for limit messages via final_text variable before closing
    # But since final_text isn't in scope here, the above should catch it. If it doesn't,
    # the exact matched text "You've reached your limit of 20 Grok Auto questions" will.
        
    return response_text

def query_grok(prompt: str, timeout_seconds=420, max_retries=5) -> str:
    print(f"[*] Querying Grok... (Prompt length: {len(prompt)})")
    
    for attempt in range(max_retries):
        result = _query_grok_single(prompt, timeout_seconds)
        
        if result == "RATE_LIMIT_REACHED":
            print(f"[-] Grok rate limit reached on attempt {attempt+1}/{max_retries}. Rotating cookies...")
            rotate_cookie()
            time.sleep(2)
            continue
            
        if result == "SERVICE_UNAVAILABLE":
            print(f"[-] Grok service unavailable on attempt {attempt+1}/{max_retries}. Rotating cookies and retrying...")
            rotate_cookie()
            time.sleep(5)
            continue

        if not result and attempt < max_retries - 1:
            print(f"[-] Grok returned empty on attempt {attempt+1}/{max_retries}. Rotating cookies and retrying...")
            rotate_cookie()
            time.sleep(5)
            continue
            
        return result
        
    print("[-] All Grok attempts exhausted (rate limits, service issues, or timeouts).")
    return ""

if __name__ == "__main__":
    # Test block
    print("Testing grok_reporter with real prompt...")
    
    real_prompt = """You are my dedicated OSINT analyst. ALWAYS respond ONLY in this exact format:

*Aoa, sir*

🔶Subject : *OSINT Update – [Title]*

🔹[First fact]
🔹[Second fact]

🔶 *Sentiment*: [Sentiment]

Links:
https://x.com/fake/123

 *Regards*

Please generate a fake report using this EXACT format for a test event where aliens land on Earth. INCLUDE the emojis and italics exactly as shown."""

    result = query_grok(real_prompt, timeout_seconds=90)
    print("\nRESULT:")
    print(result)
