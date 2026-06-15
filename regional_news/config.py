import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(BASE_DIR, "targets.json")
DB_FILE = os.path.join(BASE_DIR, "seen_posts.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")
TWITTER_COOKIES_PATH = os.path.join(BASE_DIR, "twitter_cookies.pkl")

# Telethon requires API ID and Hash. 
# These are standard public ones that work for general login, but you can replace them.
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)

# WhatsApp Forwarding Configuration
WHATSAPP_TARGET        = "Regional news"    # Category 2 – regional/local
WHATSAPP_GLOBAL_GROUP  = "Automated news"   # Category 1 – global/international
WHATSAPP_OTHER_GROUP   = "Other news"        # Category 3 – useless / junk
