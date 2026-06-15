import sys
import asyncio

from ai_reporter import generate_osint_report

def main():
    test_item = {
        "platform": "Twitter",
        "account": "FakeNewsAccount",
        "date": "2026-02-24T12:00:00Z",
        "url": "https://x.com/fake/123",
        "text": "Breaking: Heavy clashes in Nangarhar as Pakistan army loses 3 posts to TTP fighters. Massive smoke seen from the border. #DurandLine",
        "metrics": {"views": 45, "likes": 2, "reposts": 1}
    }
    
    print("Testing generate_osint_report with Qwen3-VL:4b...\n")
    report = generate_osint_report(test_item, img_path=None)
    
    with open("test_output_clean.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print("Report written to test_output_clean.txt")

if __name__ == "__main__":
    main()
