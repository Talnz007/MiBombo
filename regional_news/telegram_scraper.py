import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from config import API_ID, API_HASH, MEDIA_DIR
from utils import is_seen, mark_seen

SESSION_NAME = "telegram_session"

async def scrape_telegram(channels):
    """
    Connects to Telegram using the saved session and fetches new messages.
    """
    results = []
    
    # Check if session exists
    if not os.path.exists(f"{SESSION_NAME}.session"):
        print("[!] Telegram session not found. Please run telegram_login.py first.")
        return results

    # We enforce a timeout on the socket connection to avoid WinError 121 / 10060 hangs
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH, connection_retries=1, timeout=15)
    
    try:
        # Wrap the connection in a strict timeout
        try:
            await asyncio.wait_for(client.connect(), timeout=20.0)
        except asyncio.TimeoutError:
            print("[!] Telegram connection timed out.")
            return results
            
        if not await client.is_user_authorized():
            print("[!] Telegram session invalid or expired. Please run telegram_login.py again.")
            await client.disconnect()
            return results

        for channel in channels:
            print(f"[*] Checking Telegram channel: {channel}")
            try:
                # Get the last 15 messages max (since this runs every 5 mins, 15 is plenty)
                async for message in client.iter_messages(channel, limit=15):
                    msg_id = message.id
                    identifier = f"{channel}_{msg_id}"
                    
                    if is_seen("telegram", identifier):
                        continue # Skip already seen messages
                        
                    # Process new message
                    text = message.message or ""
                    
                    # Time filter logic
                    dt = message.date if message.date else datetime.now(timezone.utc)
                    if dt.tzinfo is None:
                         dt = dt.replace(tzinfo=timezone.utc)
                         
                    if datetime.now(timezone.utc) - dt > timedelta(minutes=6):
                         continue
                         
                    date_iso = dt.isoformat()
                    link = f"https://t.me/{channel}/{msg_id}"
                    
                    saved_media = []
                    
                    # Download media if present
                    if message.media:
                         # We only download photos or small documents/videos to save space
                         filename = f"tg_{channel}_{msg_id}"
                         try:
                             # Wrap media download in a timeout in case the connection drops mid-download
                             file_path = await asyncio.wait_for(
                                 client.download_media(message.media, file=os.path.join(MEDIA_DIR, filename)),
                                 timeout=30.0
                             )
                             if file_path:
                                 saved_media.append(file_path)
                         except asyncio.TimeoutError:
                             print(f"[!] Timeout downloading media for {link}")
                         except Exception as dl_e:
                             print(f"[!] Error downloading media for {link}: {dl_e}")

                    results.append({
                        "platform": "telegram",
                        "channel": channel,
                        "url": link,
                        "text": text,
                        "media": saved_media,
                        "date": date_iso
                    })
                    
                    mark_seen("telegram", identifier)
                    
            except Exception as e:
                print(f"[!] Error scraping channel {channel}: {e}")
                
    except Exception as e:
         print(f"[!] Error connecting to Telegram: {e}")
    finally:
         if client.is_connected():
             await client.disconnect()
         
    return results
