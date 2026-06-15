import os
import asyncio
from ai_reporter import generate_osint_report, _query_ollama
from grok_reporter import query_grok
from twitter_scraper import TWITTER_COOKIES_PATH
from whatsapp_dispatcher import send_whatsapp_pw
from config import MEDIA_DIR, WHATSAPP_TARGET

def reprocess_failed_media():
    print("[*] Reprocessing failed media items using Grok...")
    
    # Find all screenshots in MEDIA_DIR
    screenshots = [os.path.join(MEDIA_DIR, f) for f in os.listdir(MEDIA_DIR) if f.endswith(".png")]
    if not screenshots:
        print("[-] No screenshots found in output/media to reprocess.")
        return
        
    for i, img_path in enumerate(screenshots, 1):
        filename = os.path.basename(img_path)
        print(f"\n--- REPROCESSING POST #{i} ({filename}) ---")
        
        # Parse account and url from filename: twitter_zarrar_11PK_2027042613636055211_...
        parts = filename.split("_")
        if len(parts) >= 4 and parts[0] == "twitter":
            account = parts[1]
            tweet_id = parts[2]
            url = f"https://x.com/{account}/status/{tweet_id}"
        else:
            print("[-] Couldn't parse filename, skipping.")
            continue
            
        
        print(f"[*] Extracting OCR text from {filename} using local Vision Model...")
        ocr_prompt = "Extract all text from this image accurately. Do not describe the image, just output the text."
        extracted_text = _query_ollama(ocr_prompt, temperature=0.1, image_path=img_path)
        if not extracted_text or len(extracted_text.strip()) < 5:
            extracted_text = "[Failed to extract text via OCR. Image may be purely visual.]"
            
        item = {
            "platform": "twitter",
            "account": account,
            "url": url,
            "text": extracted_text,
            "date": "2026-02-26T00:00:00.000Z",
            "screenshot": img_path,
            "metrics": {}
        }
            
        print(f"[*] Passing item to local AI Reporter...")
        report = generate_osint_report(item)
        
        # Save report locally for debugging
        try:
            with open("test_output.txt", "w", encoding="utf-8") as f:
                f.write(report)
        except:
            pass

        print(f"[*] Dispatching to WhatsApp -> {WHATSAPP_TARGET}...")
        
        async def send_msg():
            _success = False
            try:
                await send_whatsapp_pw(WHATSAPP_TARGET, report, item['screenshot'])
                print(f"[+] WhatsApp message sent successfully.")
                _success = True
            except Exception as e:
                print(f"[-] Failed to send WhatsApp message: {e}")
            return _success

        success = asyncio.run(send_msg())
        
        if success:
            # Remove image if it worked
            try:
                os.remove(item['screenshot'])
                print(f"[*] Cleaned up media: {item['screenshot']}")
            except Exception as e:
                pass

if __name__ == "__main__":
    reprocess_failed_media()
