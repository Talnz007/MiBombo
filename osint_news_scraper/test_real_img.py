import asyncio
import os
from whatsapp_dispatcher import send_whatsapp_pw

async def test():
    # Use a real screenshot that exists
    img = r"H:\automatingmework\osint_news_scraper\output\media\twitter_ZardSi_2025320802871128450_1771709394825.png"
    msg = "*TWITTER ALERT*\nSource: ZardSi\nURL: https://x.com/ZardSi/status/2025320802871128450"
    
    print(f"Testing with image: {os.path.exists(img)}")
    await send_whatsapp_pw("Automated news", msg, img)
    print("[+] Test done!")

if __name__ == "__main__":
    asyncio.run(test())
