import asyncio
import os
from whatsapp_dispatcher import send_whatsapp_pw

async def test():
    print("Testing attach button with a real image...")
    # Create a small test image
    from PIL import Image
    os.makedirs("output", exist_ok=True)
    test_img = os.path.join("output", "test_attach.png")
    img = Image.new('RGB', (200, 200), color='blue')
    img.save(test_img)
    
    await send_whatsapp_pw(
        "Automated news",
        "ATTACH TEST - verifying new selector works",
        test_img
    )
    # Clean up
    if os.path.exists(test_img):
        os.remove(test_img)
    print("[+] Attach test completed!")

if __name__ == "__main__":
    asyncio.run(test())
