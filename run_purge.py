import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
from prism_organizer.config import Config
from prism_organizer.scanner import Scanner
from prism_organizer.duplicates import DuplicateDetector
from prism_organizer.executor import Executor

def main():
    config = Config()
    scanner = Scanner(config)
    detector = DuplicateDetector(config)
    executor = Executor(config)

    dirs = [
        r"C:\Users\Lenovo\Downloads",
        r"C:\Users\Lenovo\Documents",
        r"C:\Users\Lenovo\Desktop",
        r"C:\Users\Lenovo\Pictures"
    ]

    for d in dirs:
        import os
        if not os.path.exists(d):
            print(f"Skipping {d} because it does not exist.")
            continue
        print(f"Scanning {d} for duplicates...")
        scan_result = scanner.scan(target=d, recursive=True, skip_dirs=set())
        dup_result = detector.find_duplicates(scan_result)
        
        # Don't try to print report since rich display might crash, or we can just print basic stats
        print(f"Found {len(dup_result.groups)} duplicate groups in {d}")
        
        if dup_result.has_duplicates:
            print(f"Purging duplicates in {d}...")
            executor.execute_duplicate_cleanup(dup_result, d)
            print("Purge complete.")
        print("-" * 40)

if __name__ == "__main__":
    main()
