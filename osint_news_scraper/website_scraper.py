import feedparser
import requests
from bs4 import BeautifulSoup
from utils import is_seen, mark_seen
from datetime import datetime
import hashlib
import time
from urllib.parse import urlparse
from duckduckgo_search import DDGS

def scrape_duckduckgo_news(queries):
    """
    Uses DuckDuckGo to search for the latest news based on provided queries.
    """
    print(f"[*] Starting DuckDuckGo News Search for {len(queries)} queries...")
    results = []
    
    with DDGS() as ddgs:
        for query in queries:
            print(f"[*] Searching DDG News for: {query}")
            try:
                # Fetch latest news (limit to 10 per query to avoid spam)
                ddgs_gen = ddgs.news(query, region="wt-wt", safesearch="off", timelimit="d", max_results=10)
                if ddgs_gen:
                    for r in ddgs_gen:
                        link = r.get('url')
                        if not link: continue
                        
                        identifier = f"ddg_{hashlib.md5(link.encode('utf-8')).hexdigest()}"
                        if is_seen("websites", identifier):
                            continue
                            
                        results.append({
                            "platform": "website",
                            "site": "DuckDuckGo News",
                            "url": link,
                            "text": f"{r.get('title')} - {r.get('source')}",
                            "date": r.get('date') or datetime.now().isoformat()
                        })
                        mark_seen("websites", identifier)
                # Small delay to avoid aggressive rate limiting
                time.sleep(1)
            except Exception as e:
                print(f"[-] DDG Search failed for '{query}': {e}")
                
    return results

def scrape_websites(urls):
    """
    Scrapes a list of target websites for new articles.
    Attempts RSS format first, and falls back to naive HTML parsing.
    """
    print(f"[*] Starting Website Scraper for {len(urls)} sites...")
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT News Bot"
    }

    for url in urls:
        print(f"[*] Checking website/feed: {url}")
        try:
            # Fetch content with requests (more reliable timeout/retries than feedparser default)
            content = None
            for attempt in range(3):
                try:
                    resp = requests.get(url, headers=headers, timeout=60)
                    if resp.status_code == 200:
                        content = resp.text
                        break
                except Exception as e:
                    if attempt == 2: print(f"[-] Final attempt failed for {url}: {e}")
                    time.sleep(2)
            
            if not content:
                continue

            # Parse as feed or fallback to HTML
            # Note: We pass the URL here but feedparser usually accepts string content too.
            # Using content if possible is better.
            feed = feedparser.parse(content)
            
            if feed.entries:
                print(f"[+] Found {len(feed.entries)} RSS entries for {url}")
                for entry in feed.entries[:10]:
                    link = entry.get('link', '')
                    if not link:
                        continue
                        
                    identifier = f"web_{hashlib.md5(link.encode('utf-8')).hexdigest()}"
                    if is_seen("websites", identifier):
                        continue
                        
                    title = entry.get('title', 'No Title')
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        dt = datetime(*entry.published_parsed[:6]).isoformat()
                    else:
                        dt = datetime.now().isoformat()
                        
                    results.append({
                        "platform": "website",
                        "site": url,
                        "url": link,
                        "text": title,
                        "date": dt
                    })
                    mark_seen("websites", identifier)
            
            # Fallback 1: DuckDuckGo News Search for this specific site
            if not feed.entries:
                domain = urlparse(url).netloc
                print(f"[*] RSS empty for {url}. Trying DDG News Search (site:{domain})...")
                try:
                    with DDGS() as ddgs:
                        query = f"site:{domain}"
                        ddgs_gen = ddgs.news(query, region="wt-wt", safesearch="off", timelimit="d", max_results=10)
                        if ddgs_gen:
                            found_any = False
                            for r in ddgs_gen:
                                link = r.get('url')
                                if not link: continue
                                identifier = f"web_{hashlib.md5(link.encode('utf-8')).hexdigest()}"
                                if is_seen("websites", identifier): continue
                                
                                results.append({
                                    "platform": "website",
                                    "site": f"{url} (via DDG)",
                                    "url": link,
                                    "text": f"{r.get('title')} - {r.get('source')}",
                                    "date": r.get('date') or datetime.now().isoformat()
                                })
                                mark_seen("websites", identifier)
                                found_any = True
                            if found_any:
                                print(f"[+] Found results via DDG for {domain}")
                                continue
                except Exception as de:
                    print(f"[-] DDG fallback failed for {url}: {de}")

            # Fallback 2: Naive HTML parsing
            if not feed.entries and content:
                print(f"[*] Trying naive HTML parsing for {url}...")
                soup = BeautifulSoup(content, 'html.parser')
                for heading in soup.find_all(['h1', 'h2', 'h3']):
                    a_tag = heading.find('a')
                    if a_tag and a_tag.has_attr('href'):
                        href = a_tag['href']
                        if href.startswith('/'):
                            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            link = base + href
                        else:
                            link = href
                            
                        identifier = f"web_{hashlib.md5(link.encode('utf-8')).hexdigest()}"
                        if is_seen("websites", identifier):
                            continue
                            
                        title = heading.get_text(strip=True)
                        if len(title) < 10:
                            continue
                            
                        results.append({
                            "platform": "website",
                            "site": url,
                            "url": link,
                            "text": title,
                            "date": datetime.now().isoformat()
                        })
                        mark_seen("websites", identifier)
                            
        except Exception as e:
            print(f"[-] Error scraping website {url}: {e}")
            
    return results
