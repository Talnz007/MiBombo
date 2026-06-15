"""
shared_dedup.py  –  Cross-process URL deduplication for both scrapers.

Uses a shared JSON file at the workspace root, protected by msvcrt file-locking
(same pattern as whatsapp_global.lock) so both processes can safely read/write
without corrupting the file.

Usage:
    import sys, os
    sys.path.insert(0, r"H:\\automatingmework")
    from shared_dedup import is_duplicate, mark_seen, claim_url
"""

import os
import json
import hashlib

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

# ── Paths ──────────────────────────────────────────────────────────────────────
_WORKSPACE = os.path.dirname(os.path.abspath(__file__))
_SEEN_FILE = os.path.join(_WORKSPACE, "global_seen_urls.json")
_LOCK_FILE  = os.path.join(_WORKSPACE, "global_seen_urls.lock")

# ── Internal helpers ──────────────────────────────────────────────────────────

def _url_key(url: str) -> str:
    """Normalise a URL into a stable short key (SHA-256 prefix)."""
    url = url.strip().rstrip("/").lower()
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def _load_seen() -> dict:
    if not os.path.exists(_SEEN_FILE):
        return {}
    try:
        with open(_SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_seen(seen: dict) -> None:
    with open(_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def _acquire_lock(lock_fd) -> None:
    """Spin-wait until we can lock the 1-byte record."""
    while True:
        try:
            if os.name == 'nt':
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except (IOError, BlockingIOError):
            import time
            time.sleep(0.2)


def _release_lock(lock_fd) -> None:
    try:
        if os.name == 'nt':
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
    except (IOError, OSError):
        pass

# ── Public API ─────────────────────────────────────────────────────────────────

def is_duplicate(url: str) -> bool:
    """
    Returns True if this URL (or an equivalent normalised version) has already
    been seen and sent by either scraper.
    Thread/process-safe: uses a file lock.
    """
    if not url or url == "No URL":
        return False

    key = _url_key(url)
    lock_fd = open(_LOCK_FILE, "a+")
    _acquire_lock(lock_fd)
    try:
        seen = _load_seen()
        return key in seen
    finally:
        _release_lock(lock_fd)
        lock_fd.close()


def claim_url(url: str, category: int = 0, source: str = "") -> bool:
    """
    Atomically claims a URL. If it has already been seen/claimed by another process, 
    returns False. If it is new, marks it as 'claimed' and returns True.
    """
    if not url or url == "No URL":
        return False
        
    from datetime import datetime
    key = _url_key(url)
    lock_fd = open(_LOCK_FILE, "a+")
    _acquire_lock(lock_fd)
    try:
        seen = _load_seen()
        if key in seen:
            return False
            
        seen[key] = {
            "url": url,
            "category": category,
            "source": source,
            "status": "claimed",
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        _save_seen(seen)
        return True
    finally:
        _release_lock(lock_fd)
        lock_fd.close()


def mark_seen(url: str, category: int = 0, source: str = "") -> None:
    """
    Mark a URL as sent.  Stores the hash, original URL, category, and source
    for debugging.  Thread/process-safe.
    """
    if not url or url == "No URL":
        return

    from datetime import datetime
    key = _url_key(url)
    lock_fd = open(_LOCK_FILE, "a+")
    _acquire_lock(lock_fd)
    try:
        seen = _load_seen()
        if key not in seen:
            seen[key] = {
                "url": url,
                "category": category,
                "source": source,
                "status": "sent",
                "ts": datetime.utcnow().isoformat() + "Z",
            }
        else:
            # Update existing claim to 'sent'
            seen[key]["status"] = "sent"
            seen[key]["category"] = category
            if source:
                seen[key]["source"] = source
        _save_seen(seen)
    finally:
        _release_lock(lock_fd)
        lock_fd.close()
