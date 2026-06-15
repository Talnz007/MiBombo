# HP ProBook 6460b — Setup & Deployment Guide

This guide details how to clone the new root repository onto the HP ProBook 6460b and get the OSINT pipeline running, assuming the virtual environment (`venv`) and requirements are already prepared.

## 1. Initial Git Setup

Since the ProBook already has Python, `venv`, and the requirements installed, we only need to configure Git, pull the new repository, and set up the cron job.

First, set up your global Git configuration if you haven't already:

```bash
git config --global user.name "talnz007"
git config --global user.email "Talhaniazai007@gmail.com"
```

### Option A: If the directory `/home/talnz/PythonProjects/automatingwork` DOES NOT exist yet:

```bash
cd /home/talnz/PythonProjects/
git clone <URL_OF_YOUR_NEW_REPO> automatingwork
cd automatingwork
```

### Option B: If the directory exists but isn't a git repo yet (pulling into existing):

```bash
cd /home/talnz/PythonProjects/automatingwork
git init
git remote add origin <URL_OF_YOUR_NEW_REPO>
git fetch origin
git checkout main
# If you get errors about untracked files being overwritten, you may need to force it:
# git reset --hard origin/main
```

---

## 2. Setting up the Cron Job for JSON Syncing

The pipeline generates `osint_latest_news.json` and `osint_processed_reports.json` inside the nested `osint-command-center` folder. We have created a script called `sync_reports.sh` in the root repository that copies these files to a `data/` folder and pushes them to the root repository.

1. Ensure the script is executable (it should already be, but just in case):
   ```bash
   chmod +x /home/talnz/PythonProjects/automatingwork/sync_reports.sh
   ```

2. Open your crontab editor:
   ```bash
   crontab -e
   ```

3. Add the following line to run the sync script automatically (e.g., every hour):
   ```bash
   # Run the OSINT JSON sync script at the top of every hour
   0 * * * * /home/talnz/PythonProjects/automatingwork/sync_reports.sh >> /home/talnz/PythonProjects/automatingwork/sync.log 2>&1
   ```
   *(Adjust `0 * * * *` to `*/30 * * * *` if you prefer it every 30 minutes).*

---

## 3. Running the Pipeline

Since your `venv` and requirements are already prepared on this machine:

1. **Activate the virtual environment:**
   ```bash
   source /home/talnz/PythonProjects/automatingwork/venv/bin/activate
   ```

2. **Ensure Ollama is running in the background:**
   ```bash
   ollama serve
   ```
   *(Ensure you have pulled the required models: `ollama run dolphin-llama3` and `ollama run qwen3-vl:4b`)*

3. **Run the Scrapers:**
   You can run the global scraper, the regional scraper, or both.
   ```bash
   # Terminal 1: Global Pipeline
   python osint_news_scraper/main.py

   # Terminal 2: Regional Pipeline
   python regional_news/main.py
   ```

4. **Verify WhatsApp:**
   The very first time you run this on the ProBook, Playwright will open Chromium. You must scan the WhatsApp Web QR code to authenticate the `whatsapp_session`. The session is saved and shared across both scrapers.

---

## 4. Note on the Dashboard Repository
The `osint-command-center` folder contains a separate Streamlit app that has its own Git repository (`Talnz007/osint-command-center`). 
- If you make changes to the Streamlit UI code, you must `cd osint-command-center` and commit/push those changes there.
- The root repository (`automatingwork`) ignores the nested `.git` directory but uses `sync_reports.sh` to grab the JSON files produced by it.
