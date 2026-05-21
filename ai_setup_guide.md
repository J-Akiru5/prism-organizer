# 🤖 Prism Organizer — AI Setup Guide for Beginners

> A step-by-step guide to enable AI-powered file classification and smart renaming in Prism Organizer.

---

## What AI Features Do

Prism Organizer's AI features help you organize files that don't fit neatly into standard categories:

| Feature | What It Does | Example |
|---------|-------------|---------|
| **Classify Unknown** | Suggests categories for files with unknown extensions | `report.rmd` → "Documents" (89% confidence) |
| **Smart Rename** | Generates descriptive names for auto-named files | `IMG_20240315_142356.jpg` → `sunset-beach-hawaii.jpg` |

> [!IMPORTANT]
> **AI Never Acts Alone** — All AI suggestions go through the preview/confirm pipeline. No file is moved or renamed without your explicit approval.

---

## Prerequisites

Before setting up AI, make sure Prism Organizer itself is installed and working:

```bash
# Verify installation
prism-organizer --version
# Expected: prism-organizer 1.1.0

# If not working, try:
python -m prism_organizer --version
```

---

## Choose Your AI Provider

Prism Organizer supports **three providers**. Pick the one that fits your needs:

````carousel
### ☁️ Option A: OpenAI API (Cloud)
**Best for:** Highest accuracy, easiest setup  
**Cost:** ~$0.01 per 1,000 files classified  
**Requirements:** Internet connection + API key  
**Model:** `gpt-4o-mini` (default, fast and cheap)

| Pros | Cons |
|------|------|
| ✅ Most accurate | ❌ Requires internet |
| ✅ Zero local compute | ❌ Costs money (small) |
| ✅ Works on any machine | ❌ Files metadata sent to OpenAI |
<!-- slide -->
### 🦙 Option B: Ollama (Local LLM)
**Best for:** Privacy-first users, no cloud dependency  
**Cost:** Free (runs on your hardware)  
**Requirements:** ~8GB RAM, ~4GB disk for model  
**Model:** `llama3.2` (recommended)

| Pros | Cons |
|------|------|
| ✅ 100% private | ❌ Requires decent hardware |
| ✅ Completely free | ❌ Slightly less accurate |
| ✅ Works offline | ❌ Initial model download (~4GB) |
<!-- slide -->
### 🎬 Option C: LM Studio (Local, GUI)
**Best for:** Users who want a visual LLM manager  
**Cost:** Free (runs on your hardware)  
**Requirements:** ~8GB RAM, GPU recommended  
**Model:** Any GGUF model you download

| Pros | Cons |
|------|------|
| ✅ Visual model browser | ❌ Must run LM Studio app first |
| ✅ 100% private | ❌ Uses more system resources |
| ✅ Swap models easily | ❌ Windows app required |
````

---

## Setup Instructions

### Option A: OpenAI API Setup

#### Step 1: Get an API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to **API Keys** → **Create new secret key**
4. Copy the key (starts with `sk-...`)

> [!CAUTION]
> **Never share your API key or commit it to git!** Treat it like a password.

#### Step 2: Install the OpenAI Python Package

```bash
pip install openai
```

#### Step 3: Set Your API Key

You have **two options** (choose one):

**Option 3a: Environment Variable (Recommended)**
```powershell
# PowerShell — set permanently for your user account
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")

# Restart your terminal after running this command
```

**Option 3b: Config File**
Open your config file at `~/.prism-organizer/config.yaml` and edit the `ai:` section:

```yaml
ai:
  enabled: true
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "sk-your-key-here"   # ⚠️ Only if not using env var
  features:
    classify_unknown: true
    smart_rename: false          # Set to true to enable rename suggestions
  min_confidence: 0.7
```

> [!TIP]
> The environment variable approach is safer because your key never touches disk in a config file.

#### Step 4: Enable AI in Config

If you used the environment variable for your key, your config should look like this:

```yaml
ai:
  enabled: true          # ← Change from false to true
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: ""            # ← Leave empty if using OPENAI_API_KEY env var
  features:
    classify_unknown: true
    smart_rename: false   # ← Set to true to also get rename suggestions
  min_confidence: 0.7     # ← Only apply suggestions with 70%+ confidence
```

---

### Option B: Ollama Setup

#### Step 1: Install Ollama

1. Go to [ollama.com/download](https://ollama.com/download)
2. Download and run the Windows installer
3. Ollama runs as a background service automatically

#### Step 2: Download a Model

Open a terminal and pull a model:

```bash
# Recommended model (fast, good quality, ~2GB)
ollama pull llama3.2

# Alternative: smaller model (~1.3GB, faster but less accurate)
ollama pull phi3:mini

# Alternative: larger model (~4GB, most accurate)
ollama pull llama3.1
```

#### Step 3: Verify Ollama is Running

```bash
# Should return a list of installed models
ollama list

# Quick test — should return a response
ollama run llama3.2 "Hello, what are you?"
```

#### Step 4: Install the OpenAI Python Package

Even though you're using Ollama locally, the `openai` Python package is needed (Ollama exposes an OpenAI-compatible API):

```bash
pip install openai
```

#### Step 5: Configure Prism Organizer

Edit `~/.prism-organizer/config.yaml`:

```yaml
ai:
  enabled: true
  provider: "ollama"       # ← Use Ollama
  model: "llama3.2"        # ← Must match the model you pulled
  api_key: ""              # ← Not needed for Ollama
  base_url: ""             # ← Leave empty (defaults to http://localhost:11434/v1)
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

> [!NOTE]
> If Ollama is running on a different machine or port, set `base_url` to that address:
> ```yaml
> base_url: "http://192.168.1.100:11434/v1"
> ```

---

### Option C: LM Studio Setup

#### Step 1: Install LM Studio

1. Go to [lmstudio.ai](https://lmstudio.ai)
2. Download and install the Windows app
3. Launch LM Studio

#### Step 2: Download a Model

1. In LM Studio, search for a model (e.g., `Llama 3.2 3B Instruct`)
2. Click **Download**
3. Wait for the download to complete

#### Step 3: Start the Local Server

1. In LM Studio, go to the **Local Server** tab (sidebar icon: `<->`)
2. Select your downloaded model
3. Click **Start Server**
4. You should see: `Server running at http://localhost:1234`

#### Step 4: Install the OpenAI Python Package

```bash
pip install openai
```

#### Step 5: Configure Prism Organizer

Edit `~/.prism-organizer/config.yaml`:

```yaml
ai:
  enabled: true
  provider: "lmstudio"     # ← Use LM Studio
  model: "local-model"     # ← LM Studio ignores this; uses whatever model is loaded
  api_key: ""              # ← Not needed
  base_url: ""             # ← Leave empty (defaults to http://localhost:1234/v1)
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

---

## Testing Your Setup

### Test 1: Verify AI is Enabled

```bash
prism-organizer ai-classify ~/Downloads
```

**Expected output** (if working):
```
  ℹ AI classifying 5 unknown files...

  ╔══════════════════════════════════════════════════════════════╗
  ║  AI CLASSIFICATION SUGGESTIONS                              ║
  ╠════════════════╦═════════════════════╦════════════╦═════════╣
  ║ File           ║ Suggestion          ║ Confidence ║ Why     ║
  ╠════════════════╬═════════════════════╬════════════╬═════════╣
  ║ report.rmd     ║ Misc -> Documents   ║        89% ║ R Mark… ║
  ╚════════════════╩═════════════════════╩════════════╩═════════╝
```

**If AI is disabled, you'll see:**
```
  ⚠ AI features are disabled. Enable them in ~/.prism-organizer/config.yaml under the 'ai:' section.
```

**If the openai package is missing:**
```
  ⚠ The 'openai' package is required for AI features. Install with: pip install openai
```

### Test 2: Test Smart Rename (Optional)

First enable rename in your config:
```yaml
ai:
  features:
    smart_rename: true    # ← Enable this
```

Then:
```bash
prism-organizer ai-classify ~/Downloads --rename
```

### Test 3: Verify from TUI Dashboard

```bash
prism-organizer tui
```
Press `6` to run AI classify from the interactive dashboard.

---

## Configuration Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ai.enabled` | bool | `false` | Master switch for all AI features |
| `ai.provider` | string | `"openai"` | `openai`, `ollama`, or `lmstudio` |
| `ai.model` | string | `"gpt-4o-mini"` | Model name/identifier |
| `ai.api_key` | string | `""` | API key (OpenAI only). Also reads `OPENAI_API_KEY` env var |
| `ai.base_url` | string | `""` | Override server URL (for custom endpoints) |
| `ai.features.classify_unknown` | bool | `true` | Suggest categories for unknown files |
| `ai.features.smart_rename` | bool | `false` | Suggest descriptive filenames |
| `ai.min_confidence` | float | `0.7` | Minimum confidence threshold (0.0–1.0) |

### Provider Default URLs

| Provider | Default Base URL |
|----------|-----------------|
| `openai` | `https://api.openai.com/v1` (from openai package) |
| `ollama` | `http://localhost:11434/v1` or `OLLAMA_HOST` env var |
| `lmstudio` | `http://localhost:1234/v1` |

---

## Troubleshooting

### "AI features are disabled"
**Fix:** Set `ai.enabled: true` in `~/.prism-organizer/config.yaml`

### "The 'openai' package is required"
**Fix:** Run `pip install openai`

### "AI request failed (openai/gpt-4o-mini): ..."
**Common causes:**
- **Invalid API key** → Regenerate at [platform.openai.com](https://platform.openai.com)
- **No credit balance** → Add payment method at OpenAI
- **Network error** → Check internet connection

### "AI request failed (ollama/llama3.2): Connection refused"
**Common causes:**
- Ollama isn't running → Start Ollama from the system tray or run `ollama serve`
- Wrong port → Check `ollama list` works, verify base_url

### "AI request failed (lmstudio/...): Connection refused"
**Common causes:**
- LM Studio local server isn't started → Open LM Studio → Local Server → Start Server
- No model loaded → Select a model in LM Studio first

### "No unknown files to classify"
**This is normal!** It means all files in the directory already have known extensions (`.pdf`, `.jpg`, etc.). AI classification only targets files categorized as "Misc".

### Low or no suggestions appearing
**Cause:** All AI suggestions are below your `min_confidence` threshold.  
**Fix:** Lower the threshold in config:
```yaml
ai:
  min_confidence: 0.5   # Lower from 0.7 to see more suggestions
```

---

## Security Best Practices

> [!WARNING]
> ### What Gets Sent to the AI?
> 
> When using cloud providers (OpenAI), the following file metadata is sent:
> - **File name** (e.g., `report_final_v2.rmd`)
> - **File size** (e.g., `2.4 MB`)
> - **File extension** (e.g., `.rmd`)
> - **Text preview** (first ~500 chars for text files only)
> 
> **What is NOT sent:**
> - ❌ Full file contents
> - ❌ File paths (beyond the name)
> - ❌ Binary file contents (images, videos, etc.)

### Recommendations

1. **Use environment variables** for API keys, not config files
2. **Use local LLMs** (Ollama/LM Studio) if you handle sensitive files
3. **Review suggestions** before applying — AI is not perfect
4. **Set `smart_rename: false`** unless you specifically need it (reduces data sent)
5. **Add `config.yaml` to `.gitignore`** if it contains an API key (already done by default via `.prism-organizer/` in `.gitignore`)

---

## Quick Start Cheat Sheet

```bash
# 1. Install the openai package
pip install openai

# 2. Set API key (OpenAI only)
#    PowerShell:
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key", "User")
#    OR for Ollama/LM Studio: skip this step

# 3. Edit config (~/.prism-organizer/config.yaml)
#    Set: ai.enabled = true
#    Set: ai.provider = "openai" | "ollama" | "lmstudio"

# 4. Test it
prism-organizer ai-classify ~/Downloads

# 5. With rename suggestions
prism-organizer ai-classify ~/Downloads --rename
```
