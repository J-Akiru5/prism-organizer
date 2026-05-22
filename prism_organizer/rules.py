"""Custom rule engine for Prism Organizer.

Processes user-defined rules from config to match files and perform
actions like move, copy, rename, delete, and archive.
"""

import re
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from prism_organizer.config import Config
from prism_organizer.scanner import FileInfo, ScanResult
from prism_organizer.utils import expand_path, parse_size, parse_age, safe_filename


def sanitize_suggested_stem(stem: str) -> str:
    """Sanitize suggested filename stem to prevent path traversal and invalid chars.

    Strips directory separators (/ and \\), parent directory sequences (..),
    and invalid characters (: * ? \" < > |).
    """
    if not stem:
        return "renamed_file"

    sanitized = stem.replace("/", "").replace("\\", "")
    while ".." in sanitized:
        sanitized = sanitized.replace("..", "")

    invalid_chars = [':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "")

    sanitized = sanitized.strip(". ")
    if not sanitized:
        sanitized = "renamed_file"
    return sanitized


def sanitize_filename_traversal(filename: str) -> str:
    """Sanitize a full filename (stem + extension) to prevent path traversal and invalid chars."""
    if not filename:
        return "file"
    
    if "." in filename:
        if filename.startswith(".") and filename.count(".") == 1:
            stem = filename
            suffix = ""
        else:
            stem, suffix = filename.rsplit(".", 1)
            suffix = "." + suffix
    else:
        stem = filename
        suffix = ""

    safe_stem = sanitize_suggested_stem(stem)
    safe_suffix = suffix.replace("/", "").replace("\\", "").replace("..", "")
    for char in [':', '*', '?', '"', '<', '>', '|']:
        safe_suffix = safe_suffix.replace(char, "")

    if safe_suffix and not safe_suffix.startswith("."):
        safe_suffix = "." + safe_suffix
    return safe_stem + safe_suffix


@dataclass
class RuleMatch:
    """A file matched by a rule."""
    file_info: FileInfo
    rule_name: str
    action: str
    destination: Optional[Path] = None
    new_name: Optional[str] = None


@dataclass
class RulePlan:
    """Plan of all rule matches to execute."""
    matches: List[RuleMatch] = field(default_factory=list)
    unmatched: List[FileInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_matches(self) -> int:
        """Return the total number of matched files."""
        return len(self.matches)
    
    @property
    def by_rule(self) -> Dict[str, List[RuleMatch]]:
        """Group matches by rule name for reporting."""
        groups: Dict[str, List[RuleMatch]] = {}
        for match in self.matches:
            groups.setdefault(match.rule_name, []).append(match)
        return groups


class RuleEngine:
    """Processes custom rules from configuration."""

    def __init__(self, config: Config):
        self.config = config
        self.rules = config.custom_rules

    def evaluate(self, scan_result: ScanResult) -> RulePlan:
        """Evaluate all rules against scanned files.
        
        Rules are applied in order. Each file is matched by the first
        rule that matches it. Files that don't match any rule go to unmatched.
        
        Args:
            scan_result: Results from a directory scan.
        
        Returns:
            RulePlan with all matches and planned actions.
        """
        plan = RulePlan()
        
        if not self.rules:
            plan.unmatched = list(scan_result.files)
            return plan
        
        for file_info in scan_result.files:
            matched = False
            for rule in self.rules:
                try:
                    if self._matches_rule(file_info, rule):
                        action = rule.get("action", "move")
                        dest = None
                        new_name = None
                        
                        if "destination" in rule:
                            dest_dir = expand_path(rule["destination"])
                            dest = safe_filename(dest_dir, file_info.name)
                        
                        if "rename_pattern" in rule:
                            new_name = self._apply_rename_pattern(
                                rule["rename_pattern"], file_info
                            )
                            if new_name:
                                new_name = sanitize_filename_traversal(new_name)
                        
                        plan.matches.append(RuleMatch(
                            file_info=file_info,
                            rule_name=rule.get("name", "Unnamed rule"),
                            action=action,
                            destination=dest,
                            new_name=new_name,
                        ))
                        matched = True
                        break  # First matching rule wins
                except Exception as e:
                    plan.errors.append(f"Error evaluating rule '{rule.get('name', '?')}' on {file_info.name}: {e}")
            
            if not matched:
                plan.unmatched.append(file_info)
        
        return plan

    def _matches_rule(self, file_info: FileInfo, rule: Dict[str, Any]) -> bool:
        """Check if a file matches all conditions in a rule.
        
        All conditions within a rule's ``match`` block are ANDed together.
        A rule with an empty ``match`` block matches nothing.
        
        Supported conditions:
            extension: Single extension string or list of extensions.
            name_contains: Substring match on the filename (case-insensitive).
            name_matches: Regex match against the file stem (case-insensitive).
            size_gt: File must be larger than this size (e.g. ``"10MB"``).
            size_lt: File must be smaller than this size.
            older_than: File must be older than this age (e.g. ``"30d"``).
            newer_than: File must be newer than this age.
            path_contains: Substring match on the full path (case-insensitive).
        
        Args:
            file_info: Metadata for the file being tested.
            rule: A single rule dictionary from the config.
        
        Returns:
            True if the file satisfies every condition in the rule.
        """
        match_conditions = rule.get("match", {})
        
        if not match_conditions:
            return False
        
        # Extension match
        if "extension" in match_conditions:
            ext = match_conditions["extension"]
            if isinstance(ext, list):
                if file_info.extension.lower() not in [e.lower() for e in ext]:
                    return False
            elif file_info.extension.lower() != ext.lower():
                return False
        
        # Name contains
        if "name_contains" in match_conditions:
            if match_conditions["name_contains"].lower() not in file_info.name.lower():
                return False
        
        # Name matches (regex)
        if "name_matches" in match_conditions:
            pattern = match_conditions["name_matches"]
            stem = Path(file_info.name).stem
            if not re.search(pattern, stem, re.IGNORECASE):
                return False
        
        # Size greater than
        if "size_gt" in match_conditions:
            threshold = parse_size(match_conditions["size_gt"])
            if file_info.size <= threshold:
                return False
        
        # Size less than
        if "size_lt" in match_conditions:
            threshold = parse_size(match_conditions["size_lt"])
            if file_info.size >= threshold:
                return False
        
        # Older than
        if "older_than" in match_conditions:
            max_age = parse_age(match_conditions["older_than"])
            file_age = time.time() - file_info.modified.timestamp()
            if file_age < max_age:
                return False
        
        # Newer than
        if "newer_than" in match_conditions:
            min_age = parse_age(match_conditions["newer_than"])
            file_age = time.time() - file_info.modified.timestamp()
            if file_age > min_age:
                return False
        
        # Path contains
        if "path_contains" in match_conditions:
            if match_conditions["path_contains"].lower() not in str(file_info.path).lower():
                return False
        
        return True

    @staticmethod
    def _apply_rename_pattern(pattern: str, file_info: FileInfo,
                              counter: int = 0) -> str:
        """Apply a rename pattern to generate a new filename.
        
        Supported placeholders:
            {name} - original filename without extension
            {ext} - file extension (with dot)
            {date} - modification date as YYYY-MM-DD
            {datetime} - modification datetime as YYYY-MM-DD_HHMMSS
            {counter} - sequential counter (passed by executor)
            {category} - file category
        
        Args:
            pattern: Format string with placeholders.
            file_info: Metadata for the file being renamed.
            counter: Sequential counter value for {counter} placeholder.
        
        Returns:
            The new filename with placeholders resolved.
        """
        stem = Path(file_info.name).stem
        return pattern.format(
            name=stem,
            ext=file_info.extension,
            date=file_info.modified.strftime("%Y-%m-%d"),
            datetime=file_info.modified.strftime("%Y-%m-%d_%H%M%S"),
            counter=counter,
            category=file_info.category,
        )
