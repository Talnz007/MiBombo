import asyncio
import os
from ai_reporter import generate_osint_report

def main():
    print("Testing Local Qwen2-VL Generation...")
    
    # We will use the test image from the previous session if it exists
    # Assuming the Twitter post from the user prompt:
    img_path = "test_img.png"
    
    # Fallback to the real twitter screenshot path from media/ if it's there
    media_dir = "output/media"
    if os.path.exists(media_dir):
        files = os.listdir(media_dir)
        if files:
            img_path = os.path.join(media_dir, files[0])
            
    # Look for the specific image from the prompt to make it perfect
    # if it doesn't exist, we'll just test the AI on any image
            
    mock_item = {
        "platform": "twitter",
        "account": "@TahirJan660690",
        "url": "https://x.com/TahirJan660690/status/2026698667122422011",
        "date": "2026-02-25T16:39:51.000Z",
        "text": "پاکستانی جہاا'دی تنظیم (ٹی ٹی پی) نے آج 14 حملوں کی ذمہ داری قبول کی ہے۔ جس میں مصدقہ طور پر کم از کم 12 اہلکار ہلاک اور تین زخمی ہوئے۔ جائے عملیات ولایت جنوبی وزیرستان: 7 ولایت باجوڑ: 3 ولایت ٹانک:..."
    }

    print(f"Using image: None (forcing text model)")
    print("Sending item to Dolphin-Llama3...")
    
    # Passing None for image to force the fallback to OLLAMA_TEXT_MODEL
    report = generate_osint_report(mock_item, img_path=None)
    
    print("\n\n" + "="*50)
    print("         GENERATED OSINT REPORT")
    print("="*50)
    
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(report)
        
    print("[+] Report saved to test_output.txt")
    print("="*50)

if __name__ == "__main__":
    main()
