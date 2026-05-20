"""Release packaging utility for Prism Organizer.

Creates a clean ZIP archive of the project, excluding caches, temporary files,
and git folders.
"""

import os
import zipfile
from pathlib import Path


def create_release_zip():
    project_dir = Path(__file__).parent.resolve()
    zip_name = "prism-organizer.zip"
    zip_path = project_dir / zip_name

    # Cleanup existing zip if it exists
    if zip_path.exists():
        zip_path.unlink()

    exclude_dirs = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "prism_organizer.egg-info",
        ".prism-organizer_backup",
        "build",
        "dist",
    }

    exclude_files = {
        zip_name,
        "make_release.py",  # exclude release script itself from the output zip
    }

    print(f"Creating release archive: {zip_name}...")
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(project_dir):
            root_path = Path(root)
            
            # Prune directory tree
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file in exclude_files or file.endswith(".pyc") or file.endswith(".pyo"):
                    continue

                file_path = root_path / file
                # Get path relative to project_dir for archive path mapping
                rel_path = file_path.relative_to(project_dir)
                
                print(f"  Adding: {rel_path}")
                zf.write(file_path, rel_path)
                file_count += 1

    print(f"\nSuccessfully archived {file_count} files in {zip_path}")
    return zip_path


if __name__ == "__main__":
    create_release_zip()
