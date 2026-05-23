import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
from prism_organizer.config import Config
from prism_organizer.scanner import Scanner
import os

def main():
    config = Config()
    scanner = Scanner(config)
    
    dirs = [
        r"C:\Users\Lenovo\Downloads",
        r"C:\Users\Lenovo\Documents",
        r"C:\Users\Lenovo\Pictures"
    ]

    with open(r"c:\dev\prism-organizer\scan_result.txt", "w", encoding="utf-8") as f:
        f.write("Targeted Folder Storage Composition\n")
        f.write("===================================\n\n")

        for d in dirs:
            if not os.path.exists(d):
                continue
            scan_result = scanner.scan(target=d, recursive=True, skip_dirs=set())
            f.write(f"Folder: {d}\n")
            f.write(f"Total files: {scan_result.total_files}\n")
            f.write(f"Total size: {scan_result.total_size / (1024**3):.2f} GB\n")
            f.write("\nCategory Breakdown:\n")
            for cat, info in scan_result.by_category.items():
                cat_size = info["size"]
                f.write(f"  {cat}: {cat_size / (1024**3):.2f} GB\n")
            
            f.write("\nLargest Files:\n")
            for fi in sorted(scan_result.files, key=lambda x: x.size, reverse=True)[:5]:
                f.write(f"  {fi.size / (1024**2):.2f} MB - {fi.path}\n")
            f.write("\n" + "-"*40 + "\n\n")

if __name__ == "__main__":
    main()
