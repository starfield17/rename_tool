"""
text_match.py - Text Matching Tools

Provides string matching, replacement and other functions
"""

from typing import Optional
import re


def contains(text: str, keyword: str, case_sensitive: bool = True) -> bool:
    """
    Check if text contains keyword

    Args:
        text: Text to check
        keyword: Keyword
        case_sensitive: Whether case-sensitive

    Returns:
        Whether contains
    """
    if not keyword:
        return True

    if case_sensitive:
        return keyword in text
    else:
        return keyword.lower() in text.lower()


def replace_text(text: str, old: str, new: str, case_sensitive: bool = True) -> str:
    """
    Replace string in text

    Args:
        text: Original text
        old: String to replace
        new: Replacement string
        case_sensitive: Whether case-sensitive

    Returns:
        Replaced text
    """
    if not old:
        return text

    if case_sensitive:
        return text.replace(old, new)
    else:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        return pattern.sub(new, text)


def replace_text_once(text: str, old: str, new: str, case_sensitive: bool = True) -> str:
    """
    Replace only the first matched string

    Args:
        text: Original text
        old: String to replace
        new: Replacement string
        case_sensitive: Whether case-sensitive

    Returns:
        Replaced text
    """
    if not old:
        return text

    if case_sensitive:
        return text.replace(old, new, 1)
    else:
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        return pattern.sub(new, text, count=1)


def is_valid_filename(name: str) -> tuple[bool, Optional[str]]:
    """
    Check if filename is valid (mainly for Windows)

    Args:
        name: Filename

    Returns:
        (is_valid, error_reason)
    """
    if not name:
        return False, "Filename cannot be empty"

    # Windows invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        if char in name:
            return False, f"Filename contains invalid character: {char}"

    # Trailing space or dot
    if name.endswith(' ') or name.endswith('.'):
        return False, "Filename cannot end with space or dot"

    # Windows reserved names
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    name_upper = name.upper().split('.')[0]
    if name_upper in reserved_names:
        return False, f"Filename is a Windows reserved name: {name_upper}"

    # Path length check (simplified version, only checks filename part)
    if len(name) > 255:
        return False, "Filename exceeds 255 characters"

    return True, None


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """
    Clean invalid characters from filename

    Args:
        name: Original filename
        replacement: Replacement character

    Returns:
        Cleaned filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, replacement)

    # Remove trailing spaces and dots
    name = name.rstrip(' .')

    # Handle empty filename
    if not name:
        name = "unnamed"

    return name
