# OSINT News Scraper

An automated Open Source Intelligence (OSINT) tool designed to monitor, analyze, and report on security-related events in South Asia (specifically Pakistan, Afghanistan, and India). The system scrapes multiple platforms, uses AI to filter and summarize relevant news, and dispatches reports to WhatsApp.

## 🚀 Key Features

- **Multi-Platform Scraping**: Monitors X (formerly Twitter), Telegram, and various news websites/RSS feeds.
- **AI-Powered Analysis**: 
  - Uses **Grok** (via X.com) for high-quality, formatted reporting.
  - Fallback to local **Ollama** models (`dolphin-llama3` for text, `qwen3-vl` for images).
- **Intelligent Filtering**: Automatically identifies relevant posts using an extensive keyword list spanning regional hotspots and militant terminology.
- **WhatsApp Integration**: Automated dispatch of formatted reports and screenshots to specific WhatsApp groups.
- **Media Handling**: Captures screenshots of posts and downloads media from Telegram.
- **Robust Scraping**: Includes cookie rotation for X and persistent session management for Telegram/WhatsApp.

## 🛠 Architecture

The system follows a cyclic workflow:
1. **Scrape**: Parallel collectors fetch recent posts from X, Telegram, and news feeds.
2. **Filter**: `ai_reporter.is_relevant_post` filters content based on predefined OSINT interest areas.
3. **Analyze**: `ai_reporter` queries Grok or Ollama to generate a structured report in a specific professional format.
4. **Dispatch**: `whatsapp_dispatcher` uses Playwright to send the message and media to the target WhatsApp group.
5. **Clean**: Temporary media files are deleted after successful dispatch.

## 📋 Prerequisites

- **Python**: 3.10 or higher.
- **Ollama**: Required for local fallback and vision analysis.
  - Required models: `dolphin-llama3`, `qwen3-vl:4b`.
- **Browser**: Playwright handles Chromium installation automatically.
- **Accounts**:
  - **X**: One or more accounts for scraping (cookies are required).
  - **Telegram**: API ID and Hash from [my.telegram.org](https://my.telegram.org).
  - **WhatsApp**: A browser-based session on the machine running the scraper.

## ⚙️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd regional_news
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Configure Targets**:
   Update `targets.json` with the accounts and websites you want to monitor:
   ```json
   {
       "x_accounts": ["account1", "account2"],
       "news_websites": ["https://example.com/rss"],
       "telegram_channels": ["channel_name"]
   }
   ```

4. **Setup Sessions**:
   - **X Cookies**: Use `setup_cookies.py` or `capture_twitter_cookies.py` to save login sessions to `twitter_cookies.pkl`.
   - **Telegram**: Run `telegram_login.py` to authenticate and create `telegram_session.session`.
   - **WhatsApp**: The first time you run the dispatcher, it will prompt for QR code scanning.

## 🏃 Usage

Start the main scraper loop:
```bash
python main.py
```
The script will run in 30-minute cycles by default.

## 📂 Project Structure

- `main.py`: Entry point and parallel execution logic.
- `ai_reporter.py`: AI prompting, translation, and relevance filtering.
- `config.py`: Path configurations and API credentials.
- `grok_reporter.py`: Playwright-based interface for X's Grok.
- `twitter_scraper.py` / `telegram_scraper.py` / `website_scraper.py`: Platform-specific scrapers.
- `whatsapp_dispatcher.py`: Playwright-based WhatsApp message sender.

## 🛡 Disclaimer

This tool is for educational and research purposes only. Ensure compliance with the Terms of Service of all platforms used.
