import json
from datetime import datetime

# 1. Load global_seen_urls
with open('global_seen_urls.json', 'r', encoding='utf-8') as f:
    global_urls = json.load(f)

# Dates to filter
target_dates = ['2026-03-21', '2026-03-22', '2026-03-23']

relevant_urls = []
for k, v in global_urls.items():
    if v.get('source') == 'regional_news':
        ts = v.get('ts', '')
        if any(ts.startswith(d) for d in target_dates):
            relevant_urls.append(v['url'])

print(f"Found {len(relevant_urls)} relevant URLs in global_seen_urls.json")

# 2. Extract texts from seen_posts.json
try:
    with open('regional_news/seen_posts.json', 'r', encoding='utf-8') as f:
        seen_posts = json.load(f)
except Exception as e:
    print(f"Error loading seen_posts.json: {e}")
    seen_posts = {}

output_texts = []
url_set = set(relevant_urls)

for platform, posts in seen_posts.items():
    if isinstance(posts, list):
        for post in posts:
            if isinstance(post, dict) and post.get('url') in url_set:
                output_texts.append({
                    'url': post.get('url'),
                    'text': post.get('text', ''),
                    'date': post.get('date', '')
                })

with open('recent_regional_news.json', 'w', encoding='utf-8') as f:
    json.dump(output_texts, f, indent=4, ensure_ascii=False)

print(f"Extracted {len(output_texts)} texts into recent_regional_news.json")
