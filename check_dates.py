import json
import os

target_dates = ['2026-03-21', '2026-03-22', '2026-03-23']

print("Checking pak_afghan_news.json...")
try:
    with open('regional_news/pak_afghan_news.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        matches = [d for d in data if any(td in d.get('date', '') for td in target_dates)]
        print(f"Found {len(matches)} matches in pak_afghan_news.json")
        for m in matches[:2]:
            print(m.get('date'), m.get('text')[:50])
except Exception as e:
    print(e)
