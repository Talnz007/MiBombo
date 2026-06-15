# Automated OSINT Operations Platform

This repository contains an automated Open Source Intelligence (OSINT) pipeline for monitoring, processing, and disseminating information regarding security developments in South Asia (Pakistan/Afghanistan/India). 

It continuously scrapes target social media accounts and websites, processes raw data through AI (Grok/Ollama) to extract organized reports with category and priority tagging, and automatically dispatches these reports to designated WhatsApp groups.

## Project Architecture

The workspace is divided into several primary components:

### 1. `osint_news_scraper/`
The primary intelligence pipeline focusing on **global/broad** security developments.
- **Scrapers:** X/Twitter (Playwright-based), Websites (RSS/HTML), DuckDuckGo News.
- **AI Processing:** Subprocess-isolated AI generation using Grok (via Playwright) as the primary analysis engine, with local Ollama (`dolphin-llama3` / `qwen3-vl:4b`) as a fallback. Extracts exact categories (1=Global, 2=Regional, 3=Other) and priorities (1=Critical, 2=Important, 3=Routine).
- **Dispatch:** Persistent WhatsApp Web session managed by Playwright with rate limits and random jitter.

### 2. `regional_news/`
The secondary pipeline focused on **regional/local** news (Internal Pakistan/Afghanistan).
- Monitors a larger set of regional accounts (92+ X accounts).
- Direct AI reporting (no subprocess isolation).
- Different routing priorities: Regional news is prioritized.

### 3. `osint-command-center/` (Nested Repository)
An advanced Streamlit-based analytics dashboard that visualizes the JSON output of the scrapers.
- Provides 13 views including executive dashboards, timelines, geospatial maps, entity networks, and predictive intelligence.
- **Note:** This subdirectory is a separate nested git repository (`git@github.com:Talnz007/osint-command-center.git`).

### 4. Shared Infrastructure (Root)
- `shared_dedup.py`: Cross-process URL deduplication using SHA-256 hashes and file locks.
- `shared_cookie_manager.py`: Manages rotating Twitter cookies to bypass rate limits.
- `sync_reports.sh`: A utility script to copy the generated JSON reports from `osint-command-center/` and commit/push them to this root repository.

---

## Technical Stack
- **Languages:** Python 3.10+
- **Browser Automation:** Playwright, playwright-stealth
- **AI Integration:** Grok (web automated), Ollama (local LLMs)
- **Data Stores:** JSON files with file locking (`fcntl` / `msvcrt`)
- **Dashboard:** Streamlit, Folium, Pandas (Command Center)

## Quick Start
1. Ensure Python 3.10+ and `venv` are installed.
2. Install dependencies: `pip install -r requirements.txt` (and `pip install -r osint_news_scraper/requirements.txt`).
3. Run `playwright install` to download browser binaries.
4. Ensure Ollama is running (`ollama serve`) with the required models (`dolphin-llama3`, `qwen3-vl:4b`).
5. Configure your targets in `osint_news_scraper/targets.json`.
6. Run `python osint_news_scraper/main.py`.

*Note: For detailed setup instructions on specific hardware like the HP ProBook, see `SETUP_PROBOOK.md`.*
