import traceback
import sys

def main():
    try:
        import test_ai_report
        test_ai_report.main()
    except Exception as e:
        with open("crash_log.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            
if __name__ == "__main__":
    main()
