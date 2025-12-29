"""
exec_rename.py - Rename Execution Module

Responsibilities:
- Two-phase execution (first rename to temporary name, then to final name)
- Exception handling and logging
- dry_run support
"""

from pathlib import Path
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json
import os

from .models_fs import RenamePlan, RenameOp


@dataclass
class RenameResult:
    """Rename execution result"""
    success: List[RenameOp] = field(default_factory=list)
    failed: List[Tuple[RenameOp, str]] = field(default_factory=list)  # (op, error_msg)
    skipped: List[RenameOp] = field(default_factory=list)
    
    @property
    def success_count(self) -> int:
        return len(self.success)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed)
    
    @property
    def skipped_count(self) -> int:
        return len(self.skipped)
    
    def summary(self) -> str:
        """Generate summary"""
        lines = [
            f"Execution Result:",
            f"  - Success: {self.success_count}",
            f"  - Failed: {self.failed_count}",
            f"  - Skipped: {self.skipped_count}",
        ]
        if self.failed:
            lines.append("Failure Details:")
            for op, error in self.failed[:10]:  # Show at most 10
                lines.append(f"  - {op.src.name} -> {op.dst.name}: {error}")
            if len(self.failed) > 10:
                lines.append(f"  ... and {len(self.failed) - 10} more failures")
        return "\n".join(lines)


def _generate_temp_name(original: Path) -> Path:
    """Generate temporary filename"""
    unique_id = uuid.uuid4().hex[:8]
    temp_name = f".__tmp_rename__{unique_id}__{original.name}"
    return original.parent / temp_name


def _is_temp_name(name: str) -> bool:
    """Check if it's a temporary filename"""
    return name.startswith(".__tmp_rename__")


def execute_rename(
    plan: RenamePlan,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    log_dir: Optional[Path] = None
) -> RenameResult:
    """
    Execute rename plan (two-phase)

    Args:
        plan: Rename plan
        dry_run: Whether to preview only
        progress_callback: Progress callback (current, total, message)
        log_dir: Log directory (for saving execution logs)

    Returns:
        Execution result
    """
    result = RenameResult()
    valid_ops = plan.valid_ops
    total = len(valid_ops)

    if total == 0:
        return result

    # Save execution plan log
    if log_dir and not dry_run:
        save_plan_log(plan, log_dir)

    if dry_run:
        # Preview mode only
        for i, op in enumerate(valid_ops):
            if progress_callback:
                progress_callback(i + 1, total, f"[Preview] {op.src.name} -> {op.dst.name}")
            result.success.append(op)
        return result

    # Phase 1: Rename all to temporary names
    temp_mapping: List[Tuple[RenameOp, Path]] = []  # (original_op, temp_path)

    for i, op in enumerate(valid_ops):
        if progress_callback:
            progress_callback(i + 1, total * 2, f"[Phase 1] {op.src.name} -> temp name")

        if not op.src.exists():
            result.failed.append((op, "Source file does not exist"))
            continue

        # Even if source and destination are the same (only case difference), two-phase is still needed
        temp_path = _generate_temp_name(op.src)

        try:
            os.rename(op.src, temp_path)
            temp_mapping.append((op, temp_path))
        except OSError as e:
            result.failed.append((op, f"Phase 1 failed: {e}"))

    # Phase 2: Rename from temporary names to final names
    for i, (op, temp_path) in enumerate(temp_mapping):
        if progress_callback:
            progress_callback(total + i + 1, total * 2, f"[Phase 2] temp name -> {op.dst.name}")

        try:
            os.rename(temp_path, op.dst)
            result.success.append(op)
        except OSError as e:
            # Try to restore
            try:
                os.rename(temp_path, op.src)
                result.failed.append((op, f"Phase 2 failed (restored): {e}"))
            except OSError as e2:
                result.failed.append((op, f"Phase 2 failed (restore also failed): {e}, restore error: {e2}"))

    # Save execution result log
    if log_dir:
        save_result_log(result, log_dir)

    return result


def save_plan_log(plan: RenamePlan, log_dir: Path) -> Path:
    """Save execution plan log"""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"rename_plan_{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "total_ops": len(plan.valid_ops),
        "operations": [
            {
                "src": str(op.src),
                "dst": str(op.dst),
                "note": op.note
            }
            for op in plan.valid_ops
        ],
        "warnings": plan.warnings,
        "errors": plan.errors
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return log_file


def save_result_log(result: RenameResult, log_dir: Path) -> Path:
    """Save execution result log"""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"rename_result_{timestamp}.json"

    data = {
        "timestamp": timestamp,
        "success_count": result.success_count,
        "failed_count": result.failed_count,
        "skipped_count": result.skipped_count,
        "success": [
            {"src": str(op.src), "dst": str(op.dst)}
            for op in result.success
        ],
        "failed": [
            {"src": str(op.src), "dst": str(op.dst), "error": error}
            for op, error in result.failed
        ],
        "skipped": [
            {"src": str(op.src), "dst": str(op.dst)}
            for op in result.skipped
        ]
    }

    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return log_file


def cleanup_temp_files(directory: Path) -> int:
    """
    Clean up temporary files in the directory (for exception recovery)

    Args:
        directory: Directory

    Returns:
        Number of cleaned files
    """
    count = 0
    for item in directory.iterdir():
        if item.is_file() and _is_temp_name(item.name):
            # Try to restore original name
            # Temporary name format: .__tmp_rename__{uuid}__{original_name}
            parts = item.name.split("__", 3)
            if len(parts) >= 4:
                original_name = parts[3]
                original_path = directory / original_name
                if not original_path.exists():
                    try:
                        os.rename(item, original_path)
                        count += 1
                    except OSError:
                        pass
    return count
