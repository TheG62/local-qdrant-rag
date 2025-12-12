"""File system operations (create, move, copy, delete)."""

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def create_directory(path: str | Path, parents: bool = True) -> Path:
    """
    Create a directory.
    
    Args:
        path: Directory path to create
        parents: Create parent directories if needed
        
    Returns:
        Created Path object
    """
    path_obj = Path(path).expanduser()
    
    if path_obj.exists():
        if path_obj.is_dir():
            logger.warning(f"Verzeichnis existiert bereits: {path_obj}")
            return path_obj
        else:
            raise FileExistsError(f"Pfad existiert bereits als Datei: {path_obj}")
    
    path_obj.mkdir(parents=parents, exist_ok=True)
    logger.info(f"Verzeichnis erstellt: {path_obj}")
    return path_obj


def create_file(path: str | Path, content: str = "", overwrite: bool = False) -> Path:
    """
    Create a file with optional content.
    
    Args:
        path: File path to create
        content: Initial file content
        overwrite: Whether to overwrite if file exists
        
    Returns:
        Created Path object
    """
    path_obj = Path(path).expanduser()
    
    if path_obj.exists() and not overwrite:
        raise FileExistsError(f"Datei existiert bereits: {path_obj}")
    
    # Create parent directories if needed
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    path_obj.write_text(content, encoding='utf-8')
    logger.info(f"Datei erstellt: {path_obj}")
    return path_obj


def move_file_or_directory(source: str | Path, destination: str | Path) -> Path:
    """
    Move or rename a file or directory.
    
    Args:
        source: Source path
        destination: Destination path
        
    Returns:
        New Path object
    """
    source_path = Path(source).expanduser()
    dest_path = Path(destination).expanduser()
    
    if not source_path.exists():
        raise FileNotFoundError(f"Quelle existiert nicht: {source_path}")
    
    # Create parent directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(source_path), str(dest_path))
    logger.info(f"Verschoben: {source_path} -> {dest_path}")
    return dest_path


def copy_file_or_directory(source: str | Path, destination: str | Path) -> Path:
    """
    Copy a file or directory.
    
    Args:
        source: Source path
        destination: Destination path
        
    Returns:
        New Path object
    """
    source_path = Path(source).expanduser()
    dest_path = Path(destination).expanduser()
    
    if not source_path.exists():
        raise FileNotFoundError(f"Quelle existiert nicht: {source_path}")
    
    # Create parent directory if needed
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if source_path.is_dir():
        shutil.copytree(str(source_path), str(dest_path), dirs_exist_ok=True)
    else:
        shutil.copy2(str(source_path), str(dest_path))
    
    logger.info(f"Kopiert: {source_path} -> {dest_path}")
    return dest_path


def delete_file_or_directory(path: str | Path, force: bool = False) -> bool:
    """
    Delete a file or directory.
    
    Args:
        path: Path to delete
        force: Skip confirmation (use with caution!)
        
    Returns:
        True if deleted successfully
    """
    path_obj = Path(path).expanduser()
    
    if not path_obj.exists():
        raise FileNotFoundError(f"Pfad existiert nicht: {path_obj}")
    
    if path_obj.is_dir():
        shutil.rmtree(str(path_obj))
        logger.info(f"Verzeichnis gelöscht: {path_obj}")
    else:
        path_obj.unlink()
        logger.info(f"Datei gelöscht: {path_obj}")
    
    return True

