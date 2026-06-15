import json

target_dates = ['2026-03-21', '2026-03-22', '2026-03-23']

with open('osint-command-center/osint_latest_news.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

relevant_news = []
for item in data:
    date = item.get('date', '')
    if any(t in date for t in target_dates):
        text = item.get('text', '').lower()
        # Look for Pakistan/Afghanistan border clashes
        if ('pak' in text or 'afg' in text) and ('clash' in text or 'border' in text or 'cross' in text or 'fire' in text or 'viola' in text):
            relevant_news.append(item)

print(f"Total recent items: {len([i for i in data if any(t in i.get('date', '') for t in target_dates)])}")
print(f"Found {len(relevant_news)} potential clash reports.")
for i, n in enumerate(relevant_news):
    print(f"\n--- Item {i+1} ---")
    print("Date:", n.get('date'))
    print("Text:", n.get('text', '')[:500])
