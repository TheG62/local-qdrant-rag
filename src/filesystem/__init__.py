"""File system operations module."""

from .navigator import (
    get_current_dir,
    set_current_dir,
    list_directory,
    navigate_to,
    get_directory_tree,
    find_files,
)

from .operations import (
    create_directory,
    create_file,
    move_file_or_directory,
    copy_file_or_directory,
    delete_file_or_directory,
)

from .organizer import (
    analyze_document_themes,
    organize_by_themes,
    find_similar_documents,
)
from .knowledge_organizer import (
    suggest_organization_structure,
    organize_with_knowledge,
)

__all__ = [
    # Navigation
    "get_current_dir",
    "set_current_dir",
    "list_directory",
    "navigate_to",
    "get_directory_tree",
    "find_files",
    # Operations
    "create_directory",
    "create_file",
    "move_file_or_directory",
    "copy_file_or_directory",
    "delete_file_or_directory",
    # Organization
    "analyze_document_themes",
    "organize_by_themes",
    "find_similar_documents",
]

