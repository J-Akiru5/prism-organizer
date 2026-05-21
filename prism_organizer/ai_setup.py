"""Interactive AI setup wizard for Prism Organizer.

Provides a guided, beginner-friendly wizard to configure AI features.
Supports three providers:
  1. OpenAI  — cloud API (requires API key)
  2. Ollama  — free, local (requires Ollama install)
  3. LM Studio — free, local GUI (requires LM Studio install)

Usage:
    from prism_organizer.ai_setup import run_ai_setup
    run_ai_setup(config)
"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml

from prism_organizer.config import Config
from prism_organizer.utils import (
    get_app_dir,
    print_header, print_success, print_error,
    print_warning, print_info, print_item,
)


# ── Provider templates ────────────────────────────────────────────────

PROVIDER_INFO = {
    "openai": {
        "name": "OpenAI (Cloud)",
        "icon": "☁️ ",
        "description": "Uses GPT-4o-mini via the OpenAI API. Requires an API key.",
        "requires": "An OpenAI API key (starts with sk-...)",
        "cost": "Pay-per-use (~$0.15 per 1M input tokens)",
        "default_model": "gpt-4o-mini",
        "base_url": "",
        "setup_steps": [
            "1. Go to https://platform.openai.com/api-keys",
            "2. Create a new API key",
            "3. Copy the key (starts with sk-...)",
        ],
    },
    "ollama": {
        "name": "Ollama (Local, Free)",
        "icon": "🦙",
        "description": "Runs AI models locally on your machine. Completely free.",
        "requires": "Ollama installed + a model downloaded",
        "cost": "Free (runs on your hardware)",
        "default_model": "llama3.2",
        "base_url": "http://localhost:11434/v1",
        "setup_steps": [
            "1. Download Ollama from https://ollama.com",
            "2. Install and run Ollama",
            "3. Pull a model:  ollama pull llama3.2",
            "4. Ollama runs automatically in the background",
        ],
    },
    "lmstudio": {
        "name": "LM Studio (Local, Free, GUI)",
        "icon": "🖥️ ",
        "description": "User-friendly GUI for running local AI models. Free.",
        "requires": "LM Studio installed + a model downloaded",
        "cost": "Free (runs on your hardware)",
        "default_model": "local-model",
        "base_url": "http://localhost:1234/v1",
        "setup_steps": [
            "1. Download LM Studio from https://lmstudio.ai",
            "2. Install and open LM Studio",
            "3. Search and download a model (e.g., Llama 3.2)",
            "4. Go to 'Local Server' tab and click 'Start Server'",
        ],
    },
}


def _print_divider():
    """Print a styled divider line."""
    print(f"  {'─' * 56}")


def _print_provider_card(key: str, info: dict, number: int):
    """Print a formatted provider option card."""
    print(f"\n  {info['icon']} [{number}]  {info['name']}")
    print(f"       {info['description']}")
    print(f"       Cost: {info['cost']}")


def _input_safe(prompt: str, default: str = "") -> str:
    """Safe input with default value and Ctrl+C handling."""
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
        return value if value else default
    except (KeyboardInterrupt, EOFError):
        print()
        return default


def _input_choice(prompt: str, choices: list, default: str = "") -> str:
    """Prompt user to pick from numbered choices."""
    for i, choice in enumerate(choices, 1):
        print(f"    [{i}] {choice}")
    print()
    while True:
        raw = _input_safe(prompt, default)
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        # Also accept the choice text directly
        if raw in choices:
            return raw
        print_warning(f"Please enter a number between 1 and {len(choices)}")


def _test_provider_connection(provider: str, model: str,
                               api_key: str, base_url: str) -> bool:
    """Attempt a quick test call to verify the provider works."""
    try:
        import openai
    except ImportError:
        print_warning(
            "The 'openai' Python package is not installed."
        )
        print_info("Install it with:  pip install openai")
        return False

    print_info("Testing connection...")

    try:
        if provider == "ollama":
            client = openai.OpenAI(
                base_url=base_url or "http://localhost:11434/v1",
                api_key="ollama",
            )
        elif provider == "lmstudio":
            client = openai.OpenAI(
                base_url=base_url or "http://localhost:1234/v1",
                api_key="lm-studio",
            )
        else:
            client = openai.OpenAI(
                base_url=base_url or None,
                api_key=api_key,
            )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in 5 words."}],
            max_tokens=20,
            temperature=0,
        )
        reply = response.choices[0].message.content
        print_success(f"Connection successful! AI says: {reply}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg:
            print_error(f"Cannot connect to {provider}. Is it running?")
        elif "401" in error_msg or "auth" in error_msg.lower():
            print_error("Authentication failed. Check your API key.")
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            print_error(f"Model '{model}' not found. Download it first.")
        else:
            print_error(f"Connection failed: {error_msg}")
        return False


def _save_ai_config(config: Config, provider: str, model: str,
                    api_key: str, base_url: str) -> bool:
    """Save the AI configuration to the config file."""
    config_path = config._config_path

    try:
        # Load existing config
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # Update AI section
        data["ai"] = {
            "enabled": True,
            "provider": provider,
            "model": model,
            "api_key": api_key if provider == "openai" else "",
            "base_url": base_url,
            "features": {
                "classify_unknown": True,
                "smart_rename": False,
            },
            "min_confidence": 0.7,
        }

        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write back
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        print_success(f"Configuration saved to: {config_path}")
        return True

    except Exception as e:
        print_error(f"Failed to save config: {e}")
        return False


# ── Main wizard ───────────────────────────────────────────────────────


def run_ai_setup(config: Optional[Config] = None) -> bool:
    """Run the interactive AI setup wizard.

    Walks the user through selecting a provider, entering credentials,
    testing the connection, and saving the configuration.

    Args:
        config: Optional Config instance. If None, creates a new one.

    Returns:
        True if setup completed successfully, False if cancelled.
    """
    if config is None:
        config = Config()

    print()
    print_header("AI SETUP WIZARD")
    print()
    print_info("Prism Organizer can use AI to automatically classify")
    print_info("files with unknown types and suggest better filenames.")
    print()
    print_info("Choose an AI provider to get started:")
    _print_divider()

    # ── Step 1: Choose provider ───────────────────────────────────
    providers = list(PROVIDER_INFO.keys())
    for i, key in enumerate(providers, 1):
        _print_provider_card(key, PROVIDER_INFO[key], i)

    print()
    _print_divider()
    print()

    raw = _input_safe("Select provider (1/2/3, or 'q' to cancel)", "1")
    if raw.lower() in ("q", "quit", "cancel"):
        print_info("Setup cancelled.")
        return False

    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(providers)):
            raise ValueError
        provider_key = providers[idx]
    except (ValueError, IndexError):
        print_error("Invalid selection.")
        return False

    info = PROVIDER_INFO[provider_key]
    print()
    print_success(f"Selected: {info['name']}")
    _print_divider()

    # ── Step 2: Show setup steps ──────────────────────────────────
    print()
    print_info("Setup steps:")
    for step in info["setup_steps"]:
        print_item(step, indent=4)
    print()

    # ── Step 3: Collect credentials ───────────────────────────────
    api_key = ""
    base_url = info.get("base_url", "")
    model = info["default_model"]

    if provider_key == "openai":
        print_info("Enter your OpenAI API key.")
        print_info("(You can also set OPENAI_API_KEY environment variable)")
        print()

        env_key = os.environ.get("OPENAI_API_KEY", "")
        if env_key:
            print_success("Found OPENAI_API_KEY in environment!")
            use_env = _input_safe("Use environment variable? (y/n)", "y")
            if use_env.lower() in ("y", "yes"):
                api_key = env_key
            else:
                api_key = _input_safe("API key (sk-...)")
        else:
            api_key = _input_safe("API key (sk-...)")

        if not api_key:
            print_error("API key is required for OpenAI.")
            return False

        model = _input_safe("Model name", info["default_model"])
        custom_url = _input_safe("Custom API URL (leave empty for default)", "")
        if custom_url:
            base_url = custom_url

    elif provider_key == "ollama":
        print_info("Make sure Ollama is running and you have a model pulled.")
        print()
        model = _input_safe("Model name", info["default_model"])
        custom_url = _input_safe("Ollama URL", info["base_url"])
        if custom_url:
            base_url = custom_url

    elif provider_key == "lmstudio":
        print_info("Make sure LM Studio's local server is running.")
        print()
        model = _input_safe("Model name (from LM Studio)", info["default_model"])
        custom_url = _input_safe("Server URL", info["base_url"])
        if custom_url:
            base_url = custom_url

    # ── Step 4: Test connection ───────────────────────────────────
    print()
    _print_divider()
    test_now = _input_safe("Test the connection now? (y/n)", "y")

    connection_ok = False
    if test_now.lower() in ("y", "yes"):
        connection_ok = _test_provider_connection(
            provider_key, model, api_key, base_url
        )
        if not connection_ok:
            print()
            retry = _input_safe("Save config anyway? (y/n)", "y")
            if retry.lower() not in ("y", "yes"):
                print_info("Setup cancelled. You can re-run with: prism-organizer ai-setup")
                return False

    # ── Step 5: Save config ───────────────────────────────────────
    print()
    _print_divider()
    print()

    saved = _save_ai_config(config, provider_key, model, api_key, base_url)

    if saved:
        print()
        print_success("🎉 AI features are now enabled!")
        print()
        print_info("Try it out:")
        print_item("prism-organizer ai-classify ~/Downloads")
        print_item("prism-organizer tui  (then press [6] for AI)")
        print()

        if provider_key == "openai" and api_key:
            print_warning(
                "Security tip: Consider using an environment variable instead "
                "of storing your API key in the config file."
            )
            print_item("Set OPENAI_API_KEY in your system environment variables")
            print_item("Then remove the api_key line from your config file")
            print()

    return saved
