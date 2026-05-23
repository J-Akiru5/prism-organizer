# Security Policy

## Security & Data Privacy First

Prism Organizer is designed with local-first and privacy-first principles. We believe that your file structure and metadata should belong entirely to you, and we take security and privacy seriously.

This document outlines our security practices, how to report vulnerabilities, and how we handle operational data.

---

## Reporting a Vulnerability

**DO NOT report security issues or potential vulnerabilities in public GitHub Issues.**

If you discover a security vulnerability in Prism Organizer, please report it privately by emailing us at **security@prism-organizer.dev**.

### What to Include
To help us triage and resolve the issue quickly, please include:
- A description of the vulnerability and its potential impact.
- Detailed step-by-step instructions (or a proof-of-concept script/steps) to reproduce the issue.
- The version of Prism Organizer and the OS/environment you are running.

### Our Commitment (SLA)
- **72-Hour Acknowledgement**: We will acknowledge receipt of your report within 72 hours.
- **30-Day Resolution Target**: We aim to provide a resolution (patch or workaround) within 30 days of receiving the report.
- **Coordinated Disclosure**: We ask that you give us reasonable time to resolve the issue before disclosing it publicly. Once fixed, we will publish a security advisory and credit you for the discovery (unless you prefer to remain anonymous).

---

## Supported Versions

Only the latest major/minor release is actively supported with security updates.

| Version | Supported |
| ------- | --------- |
| 1.0.x   | Yes       |
| < 1.0.0 | No        |

---

## Data Handling & Privacy Guardrails

To remain fully transparent, here is how Prism Organizer manages your data:

### 1. Local-First Execution
- All core scanner, sorter, deduplication, and cleanup routines run **strictly on your local machine**.
- No file contents, directory paths, or metadata are ever transmitted to external servers by the core organizer.

### 2. Operational Logs & Undo History
- To enable the undo/redo functionality, Prism Organizer writes transaction logs to:
  `~/.prism-organizer/logs/` (or `%USERPROFILE%\.prism-organizer\logs\` on Windows).
- These logs contain **absolute file paths** of the organized files.
- These logs are stored **entirely locally** in a plain text/JSON format and are **never transmitted** to any third-party or cloud service.
- If you wish to purge these logs, you can safely delete the contents of the logs directory at any time, though this will disable the ability to undo past operations.

### 3. AI Feature & Privacy Interception
Prism Organizer includes optional AI-powered classification. Depending on your configuration, privacy behaviors are as follows:

- **Local AI Providers (e.g., Ollama, Local Llama)**:
  - If configured to use a local AI server, all prompts and file analyses remain on your local machine. No data is transmitted externally.
- **Cloud AI Providers (e.g., OpenAI, Anthropic, Gemini)**:
  - If configured to use cloud models, only the **filenames** and **short text snippets** (limited to the first 500 characters of text/code files) are transmitted to the cloud API endpoint for classification.
  - No binary contents or full files are ever uploaded.
- **AI Preview Opt-Out**:
  - You can configure Prism Organizer to operate in a metadata-only classification mode by setting `disable_previews: true` in your configuration (`config.yaml`), or by using the `--no-ai` command-line flag to disable AI classification entirely. When previews are disabled, **no file content** is read or transmitted; classification is determined solely by file extension and name.
