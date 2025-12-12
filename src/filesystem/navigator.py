"""File system navigation and exploration functions."""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Current working directory for navigation (session-based)
_current_dir: Optional[Path] = None


def get_current_dir() -> Path:
    """Get current working directory for navigation."""
    global _current_dir
    if _current_dir is None:
        _current_dir = Path.cwd()
    return _current_dir


def set_current_dir(path: str | Path) -> Path:
    """Set current working directory for navigation."""
    global _current_dir
    path_obj = Path(path).expanduser().resolve()
    
    if not path_obj.exists():
        raise FileNotFoundError(f"Pfad existiert nicht: {path_obj}")
    
    if not path_obj.is_dir():
        raise ValueError(f"Pfad ist kein Verzeichnis: {path_obj}")
    
    _current_dir = path_obj
    logger.info(f"Current directory changed to: {_current_dir}")
    return _current_dir


def list_directory(path: Optional[str | Path] = None, show_hidden: bool = False) -> Dict[str, List[Dict[str, any]]]:
    """
    List directory contents.
    
    Args:
        path: Directory path (uses current dir if None)
        show_hidden: Whether to show hidden files/directories
        
    Returns:
        Dict with 'files' and 'directories' lists
    """
    if path is None:
        path = get_current_dir()
    else:
        path = Path(path).expanduser()
    
    if not path.exists():
        raise FileNotFoundError(f"Pfad existiert nicht: {path}")
    
    if not path.is_dir():
        raise ValueError(f"Pfad ist kein Verzeichnis: {path}")
    
    files = []
    directories = []
    
    try:
        for item in path.iterdir():
            # Skip hidden files if not requested
            if not show_hidden and item.name.startswith('.'):
                continue
            
            item_info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size if item.is_file() else None,
            }
            
            if item.is_file():
                item_info["type"] = "file"
                item_info["extension"] = item.suffix
                files.append(item_info)
            elif item.is_dir():
                item_info["type"] = "directory"
                # Count items in directory
                try:
                    item_info["item_count"] = len(list(item.iterdir()))
                except PermissionError:
                    item_info["item_count"] = "?"
                directories.append(item_info)
    
    except PermissionError as e:
        logger.warning(f"Keine Berechtigung für {path}: {e}")
        raise PermissionError(f"Keine Berechtigung für Verzeichnis: {path}")
    
    return {
        "path": str(path),
        "files": sorted(files, key=lambda x: x["name"].lower()),
        "directories": sorted(directories, key=lambda x: x["name"].lower()),
    }


def navigate_to(path: str | Path) -> Path:
    """
    Navigate to a directory (changes current working directory).
    
    Args:
        path: Directory path (can be relative or absolute)
        
    Returns:
        New current directory Path
    """
    current = get_current_dir()
    
    # Handle relative paths
    if isinstance(path, str) and not Path(path).is_absolute():
        new_path = current / path
    else:
        new_path = Path(path).expanduser()
    
    return set_current_dir(new_path)


def get_directory_tree(path: Optional[str | Path] = None, max_depth: int = 3, current_depth: int = 0) -> List[str]:
    """
    Get directory tree structure.
    
    Args:
        path: Root directory (uses current dir if None)
        max_depth: Maximum depth to traverse
        current_depth: Current depth (for recursion)
        
    Returns:
        List of formatted tree lines
    """
    if path is None:
        path = get_current_dir()
    else:
        path = Path(path).expanduser()
    
    if not path.exists() or not path.is_dir():
        return []
    
    lines = []
    prefix = "  " * current_depth
    
    try:
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        
        for i, item in enumerate(items):
            if item.name.startswith('.'):
                continue
            
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                if current_depth < max_depth:
                    sub_lines = get_directory_tree(item, max_depth, current_depth + 1)
                    lines.extend(sub_lines)
            else:
                size = item.stat().st_size
                size_str = _format_size(size)
                lines.append(f"{prefix}{connector}{item.name} ({size_str})")
    
    except PermissionError:
        lines.append(f"{prefix}⚠️ Keine Berechtigung")
    
    return lines


def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def find_files(
    pattern: str,
    directory: Optional[str | Path] = None,
    recursive: bool = True,
) -> List[Dict[str, any]]:
    """
    Find files matching a pattern.
    
    Args:
        pattern: File name pattern (supports wildcards)
        directory: Search directory (uses current dir if None)
        recursive: Whether to search recursively
        
    Returns:
        List of matching file info dicts
    """
    if directory is None:
        directory = get_current_dir()
    else:
        directory = Path(directory).expanduser()
    
    if not directory.exists():
        raise FileNotFoundError(f"Verzeichnis existiert nicht: {directory}")
    
    matches = []
    search_pattern = f"**/{pattern}" if recursive else pattern
    
    try:
        for file_path in directory.glob(search_pattern):
            if file_path.is_file():
                matches.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "extension": file_path.suffix,
                })
    except Exception as e:
        logger.error(f"Fehler beim Suchen: {e}")
    
    return sorted(matches, key=lambda x: x["path"])

