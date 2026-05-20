"""Dry-run preview system for Prism Organizer.

Displays a formatted preview of planned operations and prompts
for user confirmation before executing.  Uses Rich panels and tables
when the ``rich`` library is available.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from prism_organizer.sorter import SortPlan, SortOperation
from prism_organizer.duplicates import DuplicateResult
from prism_organizer.cleaner import CleanupPlan
from prism_organizer.rules import RulePlan
from prism_organizer.display import (
    display_header, display_table, display_info, display_warning,
    display_success, display_operation_summary,
)
from prism_organizer.interactive import interactive_confirm
from prism_organizer.utils import format_size


class Preview:
    """Displays dry-run previews of planned operations.

    Uses Rich panels/tables for display and arrow-key prompts for
    confirmation when questionary is installed.
    """

    @staticmethod
    def _confirm(prompt: str, default: bool = False) -> bool:
        """Ask user for confirmation using arrow-key or text prompt."""
        return interactive_confirm(prompt, default=default)

    def show_sort_preview(self, plan: SortPlan) -> bool:
        """Show a preview of sort operations and ask for confirmation."""
        sort_label = "Sort by Type" if plan.sort_by == "type" else "Sort by Date"
        display_header("PRISM ORGANIZER -- DRY RUN")

        extra = []
        if plan.skipped:
            extra.append(("Skipped", f"{len(plan.skipped)} files in subdirectories"))

        display_operation_summary(
            command=sort_label,
            target_dir=str(plan.target_dir),
            count=plan.total_files,
            size=plan.total_size,
            extra=extra,
        )

        # Category breakdown table
        categories = plan.categories
        sorted_cats = sorted(
            categories.items(),
            key=lambda x: sum(op.file_info.size for op in x[1]),
            reverse=True,
        )

        rows = []
        for cat_name, ops in sorted_cats:
            cat_size = sum(op.file_info.size for op in ops)
            sample = ", ".join(op.file_info.name for op in ops[:3])
            if len(ops) > 3:
                sample += f", ... and {len(ops) - 3} more"
            rows.append((f"{cat_name}/", f"{len(ops)}", format_size(cat_size), sample))

        display_table(
            title="Planned Moves by Category",
            columns=[
                {"header": "Folder", "width": 15},
                {"header": "Files", "justify": "right", "width": 8},
                {"header": "Size", "justify": "right", "width": 14},
                {"header": "Sample Files", "width": 40},
            ],
            rows=rows,
        )

        return self._confirm("Execute these operations?")

    def show_cleanup_preview(self, plan: CleanupPlan) -> bool:
        """Show a preview of cleanup operations."""
        display_header("PRISM ORGANIZER -- CLEANUP PREVIEW")

        display_operation_summary(
            command="clean",
            target_dir="(scanned directory)",
            count=plan.total_items,
            size=plan.total_size,
        )

        for category, items in plan.by_category.items():
            cat_size = sum(i.size for i in items)
            cat_labels = {
                "junk": "Junk/Temp Files",
                "installer": "Large Installers",
                "zip_extracted": "Archives with Extracted Folders",
                "empty_dir": "Empty Directories",
            }
            label = cat_labels.get(category, category)

            rows = []
            for item in items[:10]:
                action = item.action.upper() if item.action != "suggest" else "SUGGEST"
                rows.append((action, item.path.name, item.reason))
            if len(items) > 10:
                rows.append(("", f"... and {len(items) - 10} more", ""))

            display_table(
                title=f"{label} ({len(items)} items, {format_size(cat_size)})",
                columns=[
                    {"header": "Action", "width": 10},
                    {"header": "File", "width": 35},
                    {"header": "Reason", "width": 40},
                ],
                rows=rows,
            )

        print()
        return self._confirm("Execute cleanup?")

    def show_duplicates_preview(self, result: DuplicateResult) -> bool:
        """Show duplicate detection results and ask for cleanup confirmation."""
        if not result.has_duplicates:
            display_success("No duplicate files found!")
            return False

        display_header("PRISM ORGANIZER -- DUPLICATE CLEANUP")

        display_operation_summary(
            command="dupes --clean",
            target_dir="(scanned directory)",
            count=result.total_duplicates,
            size=result.total_wasted_space,
            extra=[
                ("Groups", str(len(result.groups))),
            ],
        )

        # Show top 10 groups
        for i, group in enumerate(result.groups[:10], 1):
            rows = []
            for j, fi in enumerate(group.files):
                if j == 0:
                    rows.append(("[KEEP]", fi.path.name, str(fi.path.parent)))
                else:
                    rows.append(("[REMOVE]", fi.path.name, str(fi.path.parent)))

            display_table(
                title=f"Group {i}: {group.count} copies, {format_size(group.file_size)} each",
                columns=[
                    {"header": "Status", "width": 10, "style": "green" if i % 2 == 0 else ""},
                    {"header": "Filename", "width": 40},
                    {"header": "Location", "width": 30},
                ],
                rows=rows,
            )

        if len(result.groups) > 10:
            display_info(f"... and {len(result.groups) - 10} more groups")

        print()
        return self._confirm("Remove duplicate files? (originals are backed up)")

    def show_rules_preview(self, plan: RulePlan) -> bool:
        """Show preview of custom rule matches."""
        display_header("PRISM ORGANIZER -- CUSTOM RULES PREVIEW")

        display_operation_summary(
            command="rules",
            target_dir="(scanned directory)",
            count=plan.total_matches,
            size=0,
            extra=[
                ("Unmatched", str(len(plan.unmatched))),
            ],
        )

        for rule_name, matches in plan.by_rule.items():
            total_size = sum(m.file_info.size for m in matches)
            rows = []
            for match in matches[:10]:
                dest_str = ""
                if match.destination:
                    dest_str = f"-> {match.destination.parent.name}/"
                if match.new_name:
                    dest_str += f" as {match.new_name}"
                rows.append((
                    match.action.upper(),
                    match.file_info.name,
                    dest_str,
                    format_size(match.file_info.size),
                ))
            if len(matches) > 10:
                rows.append(("", f"... and {len(matches) - 10} more", "", ""))

            display_table(
                title=f"{rule_name} ({len(matches)} files, {format_size(total_size)})",
                columns=[
                    {"header": "Action", "width": 10},
                    {"header": "File", "width": 35},
                    {"header": "Destination", "width": 30},
                    {"header": "Size", "justify": "right", "width": 12},
                ],
                rows=rows,
            )

        if plan.errors:
            display_warning(f"{len(plan.errors)} errors during rule evaluation")
            for err in plan.errors[:3]:
                display_warning(err)

        print()
        return self._confirm("Execute rule actions?")
