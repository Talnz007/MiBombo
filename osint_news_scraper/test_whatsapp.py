import asyncio
import os
from whatsapp_dispatcher import send_whatsapp_pw

async def test_whatsapp():
    print("==========================================")
    print("   TESTING WHATSAPP DISPATCHER           ")
    print("==========================================")
    print("[*] This will open WhatsApp Web in a custom browser.")
    print("[*] Please scan the QR code to log in if prompted.")
    
    group_name = "Automated news"
    message = "Test message from OSINT News Scraper. Verifying WhatsApp connection!"
    
    # We will use the blank image just to test the logic
    # But first ensure it exists
    blank_img = os.path.join("output", "blank_msg.png")
    if not os.path.exists(blank_img):
        from PIL import Image
        os.makedirs("output", exist_ok=True)
        Image.new('RGBA', (1, 1), (0, 0, 0, 0)).save(blank_img)
        
    await send_whatsapp_pw(group_name, message, blank_img)
    print("[+] Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
