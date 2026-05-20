"""Setup configuration for Prism Organizer."""

from setuptools import setup, find_packages
from pathlib import Path


def read_requirements():
    """Read dependencies from requirements.txt.

    Returns:
        list[str]: A list of package requirement strings.
    """
    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        return [
            line.strip()
            for line in requirements_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    return ["PyYAML", "colorama", "tqdm"]


setup(
    name="prism-organizer",
    version="1.0.0",
    author="Jeff",
    description="A portable CLI tool that scans, analyzes, and organizes files on Windows machines",
    license="MIT",
    long_description=(Path(__file__).parent / "README.md").read_text(encoding="utf-8")
    if (Path(__file__).parent / "README.md").exists()
    else "",
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=read_requirements(),
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "prism-organizer = prism_organizer.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Desktop Environment :: File Managers",
        "Topic :: System :: Filesystems",
        "License :: OSI Approved :: MIT License",
    ],
)
