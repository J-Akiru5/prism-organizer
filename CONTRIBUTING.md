# Contributing to Prism Organizer

Thank you for your interest in contributing to Prism Organizer! This document
provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs

1. **Search existing issues** — check if the bug has already been reported.
2. **Open a new issue** using the **Bug Report** template.
3. Include:
   - Windows version and Python version
   - Steps to reproduce
   - Expected vs. actual behaviour
   - Any error output or screenshots

### Requesting Features

1. **Search existing issues** for similar requests.
2. **Open a new issue** using the **Feature Request** template.
3. Describe:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives you've considered

### Submitting Pull Requests

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
2. **Make your changes** following the code style guidelines below.
3. **Add or update tests** for any new functionality.
4. **Run the test suite** to make sure nothing is broken:
   ```bash
   pytest tests/ -v
   ```
5. **Commit** with a clear, descriptive message:
   ```bash
   git commit -m "Add cloud-drive detection timeout setting"
   ```
6. **Push** your branch and open a Pull Request against `main`.
7. Fill in the PR template and link any related issues.

## Development Setup

```bash
# Clone and install in editable mode
git clone https://github.com/J-Akiru5/prism-organizer.git
cd prism-organizer
pip install -e .

# Install dev dependencies
pip install pytest

# Run tests
pytest tests/ -v
```

## Code Style

- **Python:** Follow [PEP 8](https://peps.python.org/pep-0008/).
- **Type hints:** Use type annotations for all public function signatures.
- **Docstrings:** Use Google-style or NumPy-style docstrings for all public
  classes and functions.
- **Line length:** 100 characters maximum.
- **Imports:** Group in order — standard library, third-party, local — with a
  blank line between groups.

## Testing

- All new features should include tests in the `tests/` directory.
- Test filenames should match the module they test (e.g., `test_scanner.py`
  for `scanner.py`).
- Run the full suite before submitting:
  ```bash
  pytest tests/ -v
  ```

## Commit Messages

Use clear, imperative-mood messages:

- ✅ `Add cloud-drive detection timeout setting`
- ✅ `Fix sort-by-date crash on empty directories`
- ❌ `Updated stuff`
- ❌ `misc fixes`

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold this code.

## Questions?

Open a [Discussion](https://github.com/J-Akiru5/prism-organizer/discussions) or
reach out via an issue. We're happy to help!
