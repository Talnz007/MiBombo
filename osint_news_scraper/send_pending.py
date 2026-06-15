import asyncio
from whatsapp_dispatcher import send_whatsapp_pw

# Posts that failed to send (from the error logs)
FAILED_POSTS = [
    {
        "source": "pakafghanmatter",
        "url": "https://x.com/pakafghanmatter/status/2025317802161459641",
    },
    {
        "source": "Global_Decipher",
        "url": "https://x.com/Global_Decipher/status/2025317739145900147",
    },
    {
        "source": "thewirepak",
        "url": "https://x.com/thewirepak/status/2025320909897449579",
    },
    {
        "source": "Jan_Achakzai",
        "url": "https://x.com/Jan_Achakzai/status/2025321011860676946",
    },
    {
        "source": "ZardSi",
        "url": "https://x.com/ZardSi/status/2025320802871128450",
    },
]

async def main():
    group = "Automated news"
    for i, post in enumerate(FAILED_POSTS):
        msg = f"*TWITTER ALERT*\nSource: {post['source']}\nURL: {post['url']}"
        print(f"\n[{i+1}/{len(FAILED_POSTS)}] Sending {post['source']}...")
        try:
            # Send text only (no image)
            await send_whatsapp_pw(group, msg, None)
            print(f"[+] Sent {post['source']}")
        except Exception as e:
            print(f"[-] FAILED {post['source']}: {e}")
        await asyncio.sleep(5)
    print("\n=== ALL DONE ===")

if __name__ == "__main__":
    asyncio.run(main())
