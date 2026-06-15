import json
import os
from config import DB_FILE, MEDIA_DIR

def load_db():
    if not os.path.exists(DB_FILE):
        return {"twitter": [], "telegram": [], "websites": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"twitter": [], "telegram": [], "websites": []}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

def is_seen(platform, item_id):
    db = load_db()
    if platform not in db:
        db[platform] = []
    
    # Keep only the last 1000 items per platform to avoid huge files
    if len(db[platform]) > 1000:
        db[platform] = db[platform][-1000:]
        
    return str(item_id) in db[platform]

def mark_seen(platform, item_id):
    db = load_db()
    if platform not in db:
        db[platform] = []
    if str(item_id) not in db[platform]:
        db[platform].append(str(item_id))
    save_db(db)

def get_media_path(filename):
    return os.path.join(MEDIA_DIR, filename)
