import json

try:
    with open('regional_news/seen_posts.json', 'r', encoding='utf-8') as f:
        seen_posts = json.load(f)
    print("Type of seen_posts:", type(seen_posts))
    if isinstance(seen_posts, dict):
        k = list(seen_posts.keys())[0]
        print("First key:", k)
        print("First value type:", type(seen_posts[k]))
        if isinstance(seen_posts[k], dict):
            print("Keys of first value:", list(seen_posts[k].keys()))
            print("URL in first value:", seen_posts[k].get('url'))
    elif isinstance(seen_posts, list):
        print("First item type:", type(seen_posts[0]))
        if isinstance(seen_posts[0], dict):
            print("Keys of first item:", list(seen_posts[0].keys()))
            print("URL in first item:", seen_posts[0].get('url'))
except Exception as e:
    print("Error:", e)
