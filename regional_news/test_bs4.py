from bs4 import BeautifulSoup
import re

with open("grok_body.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
markdown_divs = soup.find_all("div", class_=re.compile("markdown", re.IGNORECASE))
print(f"Found {len(markdown_divs)} markdown divs.")

if markdown_divs:
    last_md = markdown_divs[-1]
    for tag in last_md.find_all():
        if tag.name == 'span' or tag.name == 'code':
            print("Tag:", tag.name, "| Classes:", tag.get("class"), "| Text:", tag.text[:50])

