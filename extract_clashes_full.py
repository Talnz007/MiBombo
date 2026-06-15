import json

target_dates = ['2026-03-21', '2026-03-22', '2026-03-23']

with open('osint-command-center/osint_latest_news.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

relevant_news = []
for item in data:
    date = item.get('date', '')
    if any(t in date for t in target_dates):
        text = item.get('text', '').lower()
        if ('pak' in text or 'afg' in text) and ('clash' in text or 'border' in text or 'cross' in text or 'fire' in text or 'viola' in text):
            relevant_news.append(item)

with open('clashes.json', 'w', encoding='utf-8') as f:
    json.dump(relevant_news, f, indent=4)
