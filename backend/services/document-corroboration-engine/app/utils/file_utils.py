import os
from pathlib import Path
from typing import Optional

def get_file_extension(filename: str) -> str:
    """
    Extract the file extension from a filename.
    
    Args:
        filename: The name of the file (can be a full path or just the filename)
        
    Returns:
        str: The file extension in lowercase without the dot, or an empty string if no extension
        
    Examples:
        >>> get_file_extension("document.pdf")
        'pdf'
        >>> get_file_extension("/path/to/document.pdf")
        'pdf'
        >>> get_file_extension("no_extension")
        ''
    """
    # Use pathlib to handle path operations in a cross-platform way
    path = Path(filename)
    # Get the suffix (including the dot) and remove the dot
    ext = path.suffix[1:].lower() if path.suffix else ''
    return ext

def is_valid_extension(filename: str, valid_extensions: list[str]) -> bool:
    """
    Check if a file has one of the valid extensions.
    
    Args:
        filename: The name of the file to check
        valid_extensions: List of valid extensions (without leading dots)
        
    Returns:
        bool: True if the file has a valid extension, False otherwise
    """
    if not valid_extensions:
        return True
    ext = get_file_extension(filename)
    return ext.lower() in [e.lower().lstrip('.') for e in valid_extensions]
