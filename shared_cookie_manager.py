import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
COOKIE_INDEX_FILE = os.path.join(COOKIES_DIR, "current_cookie_index.txt")

def get_current_cookie_file():
    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookie_files = sorted(glob.glob(os.path.join(COOKIES_DIR, "*.pkl")))
    if not cookie_files:
        # Fallback to older paths in case cookies directory is empty
        legacy = sorted(glob.glob(os.path.join(BASE_DIR, "osint_news_scraper", "twitter_cookies*.pkl")))
        if legacy:
            return legacy[0]
        return os.path.join(BASE_DIR, "osint_news_scraper", "twitter_cookies.pkl")
        
    try:
        if os.path.exists(COOKIE_INDEX_FILE):
            with open(COOKIE_INDEX_FILE, "r") as f:
                idx = int(f.read().strip())
        else:
            idx = 0
    except:
        idx = 0
        
    if idx >= len(cookie_files):
        idx = 0
        
    return cookie_files[idx]

def rotate_cookie():
    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookie_files = sorted(glob.glob(os.path.join(COOKIES_DIR, "*.pkl")))
    if not cookie_files:
        print("[-] No alternate cookie files found to rotate to.")
        return None
        
    try:
        if os.path.exists(COOKIE_INDEX_FILE):
            with open(COOKIE_INDEX_FILE, "r") as f:
                idx = int(f.read().strip())
        else:
            idx = 0
    except:
        idx = 0
        
    if len(cookie_files) > 1:
        idx = (idx + 1) % len(cookie_files)
        with open(COOKIE_INDEX_FILE, "w") as f:
            f.write(str(idx))
    else:
        idx = 0
        
    print(f"[*] Rotated to global cookie file: {cookie_files[idx]}")
    return cookie_files[idx]
