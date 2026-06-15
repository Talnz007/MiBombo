import asyncio
from concurrent.futures import ProcessPoolExecutor
from osint_news_scraper.ai_reporter import generate_osint_report

item = {
    "url": "https://x.com/defended/status/123",
    "text": "test tweet",
    "account": "test",
    "platform": "twitter",
    "date": "2026-02-24T12:00:00Z"
}

async def main():
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=1) as pool:
        report = await loop.run_in_executor(pool, generate_osint_report, item, None)
    print(report)

asyncio.run(main())
