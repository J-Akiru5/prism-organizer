"""Dry-run preview system for Prism Organizer.

Displays a formatted preview of planned operations and prompts
for user confirmation before executing.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from colorama import Fore, Style

from prism_organizer.sorter import SortPlan, SortOperation
from prism_organizer.duplicates import DuplicateResult
from prism_organizer.cleaner import CleanupPlan
from prism_organizer.rules import RulePlan
from prism_organizer.utils import (
    format_size, print_header, print_section, print_item,
    print_warning, print_success, print_info, confirm_action,
)


class Preview:
    """Displays dry-run previews of planned operations."""

    def show_sort_preview(self, plan: SortPlan) -> bool:
        """Show a preview of sort operations and ask for confirmation.
        
        Args:
            plan: The sort plan to preview.
        
        Returns:
            True if user confirms, False if cancelled.
        """
        sort_label = "Sort by Type" if plan.sort_by == "type" else "Sort by Date"
        print_header(f"PRISM ORGANIZER \u2014 DRY RUN")
        
        print(f"\n  {Fore.WHITE}Target:  {Fore.CYAN}{plan.target_dir}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Action:  {Fore.CYAN}{sort_label}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Files:   {Fore.CYAN}{plan.total_files} files to move{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Size:    {Fore.CYAN}{format_size(plan.total_size)}{Style.RESET_ALL}")
        
        if plan.skipped:
            print(f"  {Fore.WHITE}Skipped: {Fore.YELLOW}{len(plan.skipped)} files in subdirectories{Style.RESET_ALL}")
        
        # Show categories
        print()
        categories = plan.categories
        sorted_cats = sorted(categories.items(), key=lambda x: sum(op.file_info.size for op in x[1]), reverse=True)
        
        for cat_name, ops in sorted_cats:
            cat_size = sum(op.file_info.size for op in ops)
            print_section(cat_name, count=len(ops), size=cat_size)
            
            # Show first 3 files
            for op in ops[:3]:
                size_hint = f" ({format_size(op.file_info.size)})" if op.file_info.size > 10 * 1024 * 1024 else ""
                print_item(f"{op.file_info.name}{size_hint}")
            
            remaining = len(ops) - 3
            if remaining > 0:
                print_item(f"... and {remaining} more")
            print()
        
        return confirm_action("Execute these operations?")

    def show_cleanup_preview(self, plan: CleanupPlan) -> bool:
        """Show a preview of cleanup operations."""
        print_header("PRISM ORGANIZER \u2014 CLEANUP PREVIEW")
        
        print(f"\n  {Fore.WHITE}Items to clean: {Fore.CYAN}{plan.total_items}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Space to free:  {Fore.CYAN}{format_size(plan.total_size)}{Style.RESET_ALL}")
        
        for category, items in plan.by_category.items():
            cat_size = sum(i.size for i in items)
            cat_labels = {
                "junk": "\ud83d\uddd1  Junk/Temp Files",
                "installer": "\ud83d\udce6  Large Installers (likely installed)",
                "zip_extracted": "\ud83d\uddc3  Archives with Extracted Folders",
                "empty_dir": "\ud83d\udcc2  Empty Directories",
            }
            label = cat_labels.get(category, category)
            
            print(f"\n  {Fore.CYAN}{label} ({len(items)} items, {format_size(cat_size)}){Style.RESET_ALL}")
            for item in items[:5]:
                action_label = f"[{item.action.upper()}]" if item.action != "suggest" else "[SUGGEST]"
                name = item.path.name
                print(f"    {Fore.YELLOW}{action_label}{Style.RESET_ALL} {name} - {item.reason}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
        
        print()
        return confirm_action("Execute cleanup?")

    def show_duplicates_preview(self, result: DuplicateResult) -> bool:
        """Show duplicate detection results and ask for cleanup confirmation."""
        if not result.has_duplicates:
            print_success("No duplicate files found!")
            return False
        
        print_header("PRISM ORGANIZER \u2014 DUPLICATE CLEANUP")
        
        print(f"\n  {Fore.WHITE}Duplicate groups:  {Fore.CYAN}{len(result.groups)}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Total duplicates:  {Fore.CYAN}{result.total_duplicates}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Reclaimable space: {Fore.YELLOW}{format_size(result.total_wasted_space)}{Style.RESET_ALL}")
        
        # Show top 10 groups
        for i, group in enumerate(result.groups[:10], 1):
            print(f"\n  {Fore.CYAN}Group {i}: {group.count} copies, {format_size(group.file_size)} each{Style.RESET_ALL}")
            for j, fi in enumerate(group.files):
                if j == 0:
                    print(f"    {Fore.GREEN}[KEEP]   {fi.path.name}{Style.RESET_ALL}")
                    print(f"             {Fore.WHITE}{fi.path.parent}{Style.RESET_ALL}")
                else:
                    print(f"    {Fore.RED}[REMOVE] {fi.path.name}{Style.RESET_ALL}")
                    print(f"             {Fore.WHITE}{fi.path.parent}{Style.RESET_ALL}")
        
        if len(result.groups) > 10:
            print(f"\n  {Fore.WHITE}... and {len(result.groups) - 10} more groups{Style.RESET_ALL}")
        
        print()
        return confirm_action("Remove duplicate files? (originals are backed up)")

    def show_rules_preview(self, plan: RulePlan) -> bool:
        """Show preview of custom rule matches."""
        print_header("PRISM ORGANIZER \u2014 CUSTOM RULES PREVIEW")
        
        print(f"\n  {Fore.WHITE}Rules matched:   {Fore.CYAN}{plan.total_matches}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}Files unmatched: {Fore.YELLOW}{len(plan.unmatched)}{Style.RESET_ALL}")
        
        for rule_name, matches in plan.by_rule.items():
            total_size = sum(m.file_info.size for m in matches)
            print(f"\n  {Fore.CYAN}\u2500\u2500 {rule_name} ({len(matches)} files, {format_size(total_size)}) \u2500\u2500{Style.RESET_ALL}")
            
            for match in matches[:5]:
                action_str = match.action.upper()
                dest_str = ""
                if match.destination:
                    dest_str = f" \u2192 {match.destination.parent.name}/"
                if match.new_name:
                    dest_str += f" as {match.new_name}"
                print(f"    {Fore.YELLOW}[{action_str}]{Style.RESET_ALL} {match.file_info.name}{dest_str}")
            
            if len(matches) > 5:
                print(f"    ... and {len(matches) - 5} more")
        
        if plan.errors:
            print(f"\n  {Fore.RED}Errors: {len(plan.errors)}{Style.RESET_ALL}")
            for err in plan.errors[:3]:
                print(f"    {Fore.RED}{err}{Style.RESET_ALL}")
        
        print()
        return confirm_action("Execute rule actions?")
