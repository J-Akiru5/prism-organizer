import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
from prism_organizer.config import Config
from prism_organizer.scanner import Scanner

def main():
    config = Config()
    scanner = Scanner(config)
    print("Scanning C:\ ... (This might take a while)")
    # Scan C: recursively
    scan_result = scanner.scan(target=r"C:\Users\Lenovo", recursive=True, skip_dirs=set())
    
    with open(r"c:\dev\prism-organizer\scan_result.txt", "w", encoding="utf-8") as f:
        f.write(f"Total files: {scan_result.total_files}\n")
        f.write(f"Total size: {scan_result.total_size / (1024**3):.2f} GB\n")
        f.write(f"Oldest file: {scan_result.oldest_file.path if scan_result.oldest_file else 'None'}\n")
        f.write(f"Newest file: {scan_result.newest_file.path if scan_result.newest_file else 'None'}\n")
        
        f.write("\nCategory Breakdown:\n")
        for cat, size in scan_result.size_by_category.items():
            f.write(f"  {cat}: {size / (1024**3):.2f} GB\n")
            
        f.write("\nLargest Files:\n")
        for fi in sorted(scan_result.files, key=lambda x: x.size, reverse=True)[:50]:
            f.write(f"  {fi.size / (1024**2):.2f} MB - {fi.path}\n")

if __name__ == "__main__":
    main()
