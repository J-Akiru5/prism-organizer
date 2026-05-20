"""AI-powered file classification and renaming for Prism Organizer.

Provides optional integration with LLM providers (OpenAI, Ollama, LM Studio)
to suggest better file categories and generate descriptive filenames.

All AI features operate in *suggestion mode only* — they feed into the
existing dry-run / preview / confirm pipeline.  No file is ever moved or
renamed automatically based on an AI suggestion.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo
from prism_organizer.utils import format_size


# ── Data types ────────────────────────────────────────────────────────


@dataclass
class AIClassification:
    """An AI-suggested category for a file."""

    file_info: FileInfo
    suggested_category: str
    confidence: float          # 0.0 – 1.0
    reasoning: str = ""


@dataclass
class AIRename:
    """An AI-suggested new filename."""

    file_info: FileInfo
    new_name: str              # Stem only (no extension)
    reasoning: str = ""


@dataclass
class AIResult:
    """Aggregated results of an AI classification / rename pass."""

    classifications: List[AIClassification] = field(default_factory=list)
    renames: List[AIRename] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_suggestions(self) -> int:
        return len(self.classifications) + len(self.renames)


# ── Provider abstraction ──────────────────────────────────────────────


class AIProvider:
    """Thin wrapper around LLM providers.

    Supports:

    * ``openai``  — OpenAI API (``OPENAI_API_KEY`` env var or config)
    * ``ollama``  — Local Ollama server (``OLLAMA_HOST`` env var or
      ``http://localhost:11434``)
    * ``lmstudio`` — Local LM Studio server
      (``http://localhost:1234/v1``)

    Call :meth:`check_available` before use to confirm the required
    client library is installed.
    """

    def __init__(self, config: Config):
        ai_cfg = config.get("ai", {})
        self.enabled: bool = ai_cfg.get("enabled", False)
        self.provider: str = ai_cfg.get("provider", "openai")
        self.model: str = ai_cfg.get("model", "gpt-4o-mini")
        self.api_key: str = ai_cfg.get("api_key", "") or os.environ.get(
            "OPENAI_API_KEY", ""
        )
        self.base_url: str = ai_cfg.get("base_url", "")
        self._features: Dict[str, bool] = ai_cfg.get("features", {})
        self._min_confidence: float = ai_cfg.get("min_confidence", 0.7)

    @property
    def classify_enabled(self) -> bool:
        return self.enabled and self._features.get("classify_unknown", True)

    @property
    def rename_enabled(self) -> bool:
        return self.enabled and self._features.get("smart_rename", False)

    @property
    def min_confidence(self) -> float:
        return self._min_confidence

    def check_available(self) -> bool:
        """Return True if the provider's client library can be imported."""
        if not self.enabled:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_client(self):
        """Build and return an OpenAI-compatible client."""
        import openai

        if self.provider == "ollama":
            base = self.base_url or os.environ.get(
                "OLLAMA_HOST", "http://localhost:11434/v1"
            )
            api_key = "ollama"
        elif self.provider == "lmstudio":
            base = self.base_url or "http://localhost:1234/v1"
            api_key = "lm-studio"
        else:
            base = self.base_url or None
            api_key = self.api_key

        return openai.OpenAI(base_url=base, api_key=api_key)

    def _chat(self, system: str, user: str, **kwargs) -> Optional[str]:
        """Send a chat completion and return the response text."""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=kwargs.get("max_tokens", 500),
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(
                f"AI request failed ({self.provider}/{self.model}): {e}"
            ) from e


# ── Engine ────────────────────────────────────────────────────────────


class AIEngine:
    """Coordinates AI classification and renaming of files.

    All selections flow through the existing :class:`Preview` system —
    the engine only produces suggestion lists.
    """

    def __init__(self, config: Config):
        self.config = config
        self.provider = AIProvider(config)

        # Existing categories from config (for classification hints)
        self._categories: List[str] = list(config.categories.keys())

    def classify_unknown(
        self,
        files: List[FileInfo],
    ) -> List[AIClassification]:
        """Suggest categories for files with unknown or ``Misc`` types.

        Only files whose current category is ``Misc`` (i.e. no configured
        extension matched) are candidates.

        Args:
            files: List of file metadata from a scan.

        Returns:
            List of ``AIClassification`` suggestions, each with a
            suggested category and confidence score.
        """
        if not self.provider.check_available():
            return []

        if not self.provider.classify_enabled:
            return []

        candidates = [fi for fi in files if fi.category == "Misc"]

        if not candidates:
            return []

        results: List[AIClassification] = []

        # Batch classify in groups of 20 to stay within token limits
        batch_size = 20
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i : i + batch_size]
            try:
                batch_results = self._classify_batch(batch)
                results.extend(batch_results)
            except Exception as e:
                for fi in batch:
                    results.append(AIClassification(
                        file_info=fi,
                        suggested_category=fi.category,
                        confidence=0.0,
                        reasoning=f"Error: {e}",
                    ))

        return results

    def _classify_batch(self, files: List[FileInfo]) -> List[AIClassification]:
        """Classify a single batch of files via the LLM."""
        available_cats = ", ".join(self._categories)

        file_list = []
        for fi in files:
            preview = self._read_preview(fi)
            file_list.append(
                f"- {fi.name} ({format_size(fi.size)}, ext: {fi.extension})"
            )
            if preview:
                file_list.append(f"  preview: {preview}")

        system = (
            "You are a file organization assistant. Given a list of "
            "files with unknown categories, suggest the best category "
            "for each based on filename, extension, and content preview. "
            "Respond ONLY with a JSON object mapping filenames to "
            "classifications."
        )

        user = (
            f"Available categories: {available_cats}\n\n"
            f"Files to classify:\n" + "\n".join(file_list) + "\n\n"
            "Return a JSON object like:\n"
            '{"filename.jpg": {"category": "Images", '
            '"confidence": 0.95, "reasoning": "..."}}\n'
            "Confidence should be between 0.0 and 1.0."
        )

        response = self.provider._chat(system, user)

        # Parse JSON response
        try:
            data = self._parse_json(response)
        except (json.JSONDecodeError, ValueError):
            return [
                AIClassification(fi, fi.category, 0.0, "Could not parse AI response")
                for fi in files
            ]

        results = []
        for fi in files:
            entry = data.get(fi.name, {})
            cat = entry.get("category", fi.category)
            confidence = float(entry.get("confidence", 0))
            reasoning = entry.get("reasoning", "")
            results.append(AIClassification(fi, cat, confidence, reasoning))

        return results

    def suggest_renames(
        self,
        files: List[FileInfo],
        style: str = "descriptive",
    ) -> List[AIRename]:
        """Suggest descriptive filenames for files.

        Args:
            files: File metadata from a scan.
            style: Renaming style — ``"descriptive"`` or ``"short"``.

        Returns:
            List of :class:`AIRename` suggestions.
        """
        if not self.provider.check_available():
            return []

        if not self.provider.rename_enabled:
            return []

        # Only rename files that look auto-generated (UUID-named, IMG_*, etc.)
        candidates = [
            fi for fi in files
            if fi.is_uuid_named
            or fi.name.lower().startswith(("img_", "dsc_", "screenshot_", "untitled"))
        ]

        if not candidates:
            return []

        results: List[AIRename] = []

        batch_size = 15
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i : i + batch_size]
            try:
                batch_results = self._rename_batch(batch, style)
                results.extend(batch_results)
            except Exception as e:
                for fi in batch:
                    results.append(AIRename(
                        file_info=fi,
                        new_name=Path(fi.name).stem,
                        reasoning=f"Error: {e}",
                    ))

        return results

    def _rename_batch(
        self, files: List[FileInfo], style: str,
    ) -> List[AIRename]:
        """Rename a batch of files via the LLM."""
        file_list = []
        for fi in files:
            preview = self._read_preview(fi)
            line = f"- {fi.name} ({format_size(fi.size)}, modified: {fi.modified.date()})"
            if preview:
                line += f"\n  preview: {preview}"
            file_list.append(line)

        system = (
            "You are a file naming assistant. Generate clean, "
            f"{style} filenames (stem only, no extension) for the "
            "given files. Use lowercase with hyphens. Keep names "
            "under 60 chars. Respond ONLY with a JSON object mapping "
            "original filenames to new stems."
        )

        user = (
            "Files to rename:\n" + "\n".join(file_list) + "\n\n"
            'Return JSON like: {"old_name.jpg": {"stem": "new-name", '
            '"reasoning": "..."}}'
        )

        response = self.provider._chat(system, user)

        try:
            data = self._parse_json(response)
        except (json.JSONDecodeError, ValueError):
            return [
                AIRename(fi, Path(fi.name).stem, "Could not parse AI response")
                for fi in files
            ]

        results = []
        for fi in files:
            entry = data.get(fi.name, {})
            stem = entry.get("stem", Path(fi.name).stem)
            reasoning = entry.get("reasoning", "")
            results.append(AIRename(fi, stem, reasoning))

        return results

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _read_preview(fi: FileInfo, max_bytes: int = 2048) -> str:
        """Read a short preview of a text file's contents."""
        text_exts = {
            ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
            ".json", ".xml", ".yaml", ".yml", ".csv", ".log",
            ".java", ".c", ".cpp", ".h", ".rs", ".go", ".rb", ".php",
        }
        if fi.extension.lower() not in text_exts:
            return ""
        try:
            with open(fi.path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_bytes).replace("\n", " ")[:500]
        except Exception:
            return ""

    @staticmethod
    def _parse_json(text: Optional[str]) -> dict:
        """Extract a JSON object from LLM output (may contain markdown)."""
        if not text:
            raise ValueError("Empty AI response")

        text = text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        return json.loads(text)
