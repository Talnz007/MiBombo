import json

with open('eid_clashes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pakistan_keywords = ['balochistan', 'khyber', 'kpk', 'waziristan', 'panjgur', 'khuzdar', 'quetta', 'peshawar', 'kurram', 'dera ismail', 'gwadar', 'turbat', 'bajaur', 'mohmand', 'bannu', 'tank', 'lakki marwat', 'mianwali', 'chaman', 'surab', 'hub chowki', 'karachi', 'nasirabad', 'dera murad']

pak_attacks = []
for item in data:
    text = item.get('text', '').lower()
    if any(k in text for k in pakistan_keywords):
        pak_attacks.append(item)

with open('pak_eid_attacks.json', 'w', encoding='utf-8') as f:
    json.dump(pak_attacks, f, indent=4)
