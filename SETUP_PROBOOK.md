# HP ProBook 6460b — Setup & Deployment Guide

This guide details how to link your existing directory `/home/talnz/automating work` (which contains your active `whatsapp_session` and `venv`) to the new GitHub repository, and run the OSINT pipeline.

## 1. Connecting the Existing Directory to Git

Since `/home/talnz/automating work` already has Python, `venv`, and the `whatsapp_session` folder, we can initialize Git directly in it and sync it with the remote repository. 

> [!IMPORTANT]
> The directory name contains a space (`automating work`). In the terminal, you must escape it as `automating\ work` or wrap it in double quotes `"automating work"`.

### Step-by-Step Sync Instructions

1. **Navigate to the directory:**
   ```bash
   cd "/home/talnz/automating work"
   ```

2. **Initialize Git (if not already done):**
   ```bash
   git init
   ```

3. **Configure your Git details (if needed):**
   ```bash
   git config --global user.name "talnz007"
   git config --global user.email "Talhaniazai007@gmail.com"
   ```

4. **Add the remote repository:**
   If using SSH:
   ```bash
   git remote add origin git@github.com:Talnz007/MiBombo.git
   ```
   If using HTTPS:
   ```bash
   git remote add origin https://github.com/Talnz007/MiBombo.git
   ```

5. **Fetch the remote branch:**
   ```bash
   git fetch origin
   ```

6. **Reset to remote main branch (preserving venv and whatsapp_session):**
   Because `venv/` and `whatsapp_session/` are listed in `.gitignore`, performing a hard reset will only populate/overwrite the tracked repository files, leaving your virtual environment and WhatsApp session completely untouched:
   ```bash
   git reset --hard origin/main
   ```


---

## 2. Setting up the Cron Job for JSON Syncing

The pipeline generates `osint_latest_news.json` and `osint_processed_reports.json` inside the nested `osint-command-center` folder. We have created a script called `sync_reports.sh` in the root repository that copies these files to a `data/` folder and pushes them to the root repository.

1. Ensure the script is executable (it should already be, but just in case):
   ```bash
   chmod +x "/home/talnz/automating work/sync_reports.sh"
   ```

2. Open your crontab editor:
   ```bash
   crontab -e
   ```

3. Add the following line to run the sync script automatically (e.g., every hour):
   ```bash
   # Run the OSINT JSON sync script at the top of every hour
   0 * * * * "/home/talnz/automating work/sync_reports.sh" >> "/home/talnz/automating work/sync.log" 2>&1
   ```
   *(Adjust `0 * * * *` to `*/30 * * * *` if you prefer it every 30 minutes).*

---

## 3. Running the Pipeline

Since your `venv` and requirements are already prepared on this machine:

1. **Activate the virtual environment:**
   ```bash
   source "/home/talnz/automating work/venv/bin/activate"
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
