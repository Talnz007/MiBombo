import asyncio
import os
import sys

async def main():
    item = {
        "url": "https://x.com/defended/status/123",
        "text": "test tweet",
        "account": "test",
        "platform": "twitter",
        "date": "2026-02-24T12:00:00Z"
    }

    import main as m
    res = await m.dispatch_item(item)
    print(res)

sys.path.insert(0, os.path.join(os.getcwd(), 'osint_news_scraper'))
asyncio.run(main())
