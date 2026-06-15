import json

target_dates = ['2026-03-20', '2026-03-21', '2026-03-22', '2026-03-23']

with open('osint-command-center/osint_latest_news.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

eid_attacks = []
for item in data:
    date = item.get('date', '')
    if any(t in date for t in target_dates):
        text = item.get('text', '').lower()
        # Look for attacks in Pakistan
        # Exclude afghan stuff
        if 'afgh' not in text:
            if ('attack' in text or 'ied' in text or 'killed' in text or 'martyr' in text or 'blast' in text or 'raid' in text):
                eid_attacks.append(item)

with open('eid_clashes.json', 'w', encoding='utf-8') as f:
    json.dump(eid_attacks, f, indent=4)

print(f"Found {len(eid_attacks)} potential Eid attacks.")
