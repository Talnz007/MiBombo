
import sys
sys.path.insert(0, r'/home/talnz/PythonProjects/automatingwork/osint_news_scraper')
from grok_reporter import query_grok

print(query_grok("TEST PROMPT", timeout_seconds=60))
