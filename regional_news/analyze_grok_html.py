from bs4 import BeautifulSoup
import re

with open("grok_body.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Look at images (emojis)
print("--- IMAGES (EMOJIS) ---")
for img in soup.find_all("img"):
    print(f"Img: {img.get('src')} | Alt: {img.get('alt')} | Classes: {img.get('class')}")

# Look at spans (potential italics)
print("\n--- SPANS ---")
for span in soup.find_all("span"):
    text = span.get_text().strip()
    if text:
        # Check if it has suspicious classes
        classes = span.get("class", [])
        if any("r-1" in c for c in classes):
            print(f"Text: {text[:30]} | Classes: {classes}")
