import asyncio
import os
from whatsapp_dispatcher import send_whatsapp_pw

# All remaining screenshots that exist on disk
POSTS = [
    {
        "source": "zarrar_11PK",
        "url": "https://x.com/zarrar_11PK/status/2025316940802392139",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_zarrar_11PK_2025316940802392139_1771708437615.png"
    },
    {
        "source": "JawadYousufxai",
        "url": "https://x.com/JawadYousufxai/status/2025316907206017156",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_JawadYousufxai_2025316907206017156_1771708483957.png"
    },
    {
        "source": "miryar_baloch",
        "url": "https://x.com/miryar_baloch/status/2025317637031690395",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_miryar_baloch_2025317637031690395_1771708511163.png"
    },
    {
        "source": "BlueMist911",
        "url": "https://x.com/BlueMist911/status/2025318479403069949",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_BlueMist911_2025318479403069949_1771708554373.png"
    },
    {
        "source": "sHaidarHashmi",
        "url": "https://x.com/sHaidarHashmi/status/2025319020937830813",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_sHaidarHashmi_2025319020937830813_1771709016609.png"
    },
    {
        "source": "sHaidarHashmi",
        "url": "https://x.com/sHaidarHashmi/status/2025320386007593418",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_sHaidarHashmi_2025320386007593418_1771709015481.png"
    },
    {
        "source": "BlueMist911",
        "url": "https://x.com/BlueMist911/status/2025321493371199791",
        "img": r"H:\automatingmework\regional_news\output\media\twitter_BlueMist911_2025321493371199791_1771709332192.png"
    },
]

async def main():
    group = "Automated news"
    for i, post in enumerate(POSTS):
        if not os.path.exists(post["img"]):
            print(f"[!] Skipping {post['source']} - image missing")
            continue
        msg = f"*TWITTER ALERT*\nSource: {post['source']}\nURL: {post['url']}"
        print(f"\n[{i+1}/{len(POSTS)}] Sending {post['source']} WITH screenshot...")
        try:
            await send_whatsapp_pw(group, msg, post["img"])
            print(f"[+] Sent {post['source']}")
            # Delete the image after successful send
            try:
                os.remove(post["img"])
                print(f"[*] Cleaned up: {os.path.basename(post['img'])}")
            except:
                pass
        except Exception as e:
            print(f"[-] FAILED {post['source']}: {e}")
        await asyncio.sleep(5)
    print("\n=== ALL SCREENSHOTS SENT ===")

if __name__ == "__main__":
    asyncio.run(main())
