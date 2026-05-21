# 🤖 AI Setup Guide

Prism Organizer can use AI to automatically classify files with unknown types and suggest better filenames. This guide covers all three supported AI providers.

## Quick Start

The fastest way to set up AI is the **interactive wizard**:

```bash
prism-organizer ai-setup
```

Or from the TUI dashboard, press **[9]** to launch the setup wizard.

---

## Option 1: OpenAI (Cloud API)

**Best for:** Users who want the highest accuracy with zero local setup.  
**Cost:** Pay-per-use (~$0.15 per 1M input tokens with `gpt-4o-mini`)

### Steps

1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Go to **API Keys** → **Create new secret key**
3. Copy the key (starts with `sk-...`)

### Configuration

**Option A: Environment variable (recommended)**
```bash
# Windows (PowerShell)
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")

# Linux / macOS
export OPENAI_API_KEY="sk-your-key-here"
```

**Option B: Config file**

Edit `~/.prism-organizer/config.yaml`:

```yaml
ai:
  enabled: true
  provider: openai
  model: gpt-4o-mini
  api_key: sk-your-key-here   # ⚠️ Less secure than env var
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

> ⚠️ **Security:** Never commit your API key to version control. Prefer environment variables.

---

## Option 2: Ollama (Local, Free)

**Best for:** Users who want free, private AI running on their own machine.  
**Cost:** Free (uses your CPU/GPU)  
**Requirements:** ~4GB RAM minimum, 8GB+ recommended

### Steps

1. Download and install from [ollama.com](https://ollama.com)
2. Open a terminal and pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Ollama runs as a background service automatically

### Configuration

Edit `~/.prism-organizer/config.yaml`:

```yaml
ai:
  enabled: true
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434/v1
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

### Recommended Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `llama3.2` | 2GB | ⚡ Fast | ★★★★☆ |
| `llama3.1` | 4.7GB | ⚡ Medium | ★★★★★ |
| `mistral` | 4.1GB | ⚡ Fast | ★★★★☆ |
| `phi3` | 2.3GB | ⚡ Fast | ★★★☆☆ |

---

## Option 3: LM Studio (Local, Free, GUI)

**Best for:** Beginners who prefer a graphical interface for model management.  
**Cost:** Free (uses your CPU/GPU)

### Steps

1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Launch LM Studio and search for a model (e.g., "Llama 3.2")
3. Download the model
4. Go to the **Local Server** tab
5. Select your model and click **Start Server**

### Configuration

Edit `~/.prism-organizer/config.yaml`:

```yaml
ai:
  enabled: true
  provider: lmstudio
  model: local-model
  base_url: http://localhost:1234/v1
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

---

## Using AI Features

### Classify Unknown Files
```bash
# Scan and classify files in your Downloads folder
prism-organizer ai-classify ~/Downloads

# Also suggest smart renames for auto-generated filenames
prism-organizer ai-classify ~/Downloads --rename
```

### From the TUI Dashboard
```bash
prism-organizer tui
# Press [6] for AI classify
# Press [9] to run the AI setup wizard
```

### How It Works

1. Prism Organizer scans your directory
2. Files with "Misc" (unknown) category are sent to the AI
3. The AI suggests a better category based on filename, extension, and file content preview
4. You review the suggestions in a preview table
5. Confirm to apply the changes (or cancel)

> **Note:** AI never moves files automatically. You always get a preview and must confirm.

---

## Troubleshooting

### "openai package not installed"
```bash
pip install openai
```

### "Connection refused" (Ollama/LM Studio)
- Make sure the local server is running
- Check the URL in your config matches the server address
- Ollama: run `ollama serve` if not auto-started
- LM Studio: click "Start Server" in the Local Server tab

### "Model not found"
- Ollama: `ollama pull <model-name>`
- LM Studio: Download the model from the search tab

### "Authentication failed" (OpenAI)
- Check your API key is valid at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Ensure your account has billing set up

### Low confidence results
Lower the threshold in config:
```yaml
ai:
  min_confidence: 0.5  # Default is 0.7
```

---

## Disabling AI

Set `enabled: false` in your config:

```yaml
ai:
  enabled: false
```
