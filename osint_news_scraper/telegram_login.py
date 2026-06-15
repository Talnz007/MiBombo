import asyncio
from telethon import TelegramClient
from config import API_ID, API_HASH

# This is the session file name that will be saved in the folder
SESSION_NAME = "telegram_session"

async def main():
    print("Initializing Telegram Client...")
    print("You will be asked to enter your phone number and the login code.")
    print("The login code will be sent to the Arthur Morgan account on your PC App.")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    
    print("\n\nSUCCESS! You are logged in.")
    print("A 'telegram_session.session' file has been created in this folder.")
    print("The osint scraper can now use your account to read channels.")
    print("You can close this script now.")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
