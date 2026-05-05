"""
automation/file_control.py
File and folder management operations.
"""

import shutil
import os
import glob
from datetime import datetime
from core.logger import log_info, log_error

_copied_path = ""


def copy_file(path: str):
    global _copied_path
    if os.path.exists(path):
        _copied_path = path
        log_info(f"File copied to clipboard: {path}")
    else:
        raise FileNotFoundError(f"File not found: {path}")


def paste_file(destination: str):
    global _copied_path
    if not _copied_path:
        raise ValueError("No file copied yet.")
    if not os.path.exists(destination):
        os.makedirs(destination, exist_ok=True)
    shutil.copy(_copied_path, destination)
    log_info(f"File pasted to: {destination}")


def delete_file(path: str):
    if os.path.exists(path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        log_info(f"Deleted: {path}")
    else:
        raise FileNotFoundError(f"Not found: {path}")


def create_folder(path: str):
    os.makedirs(path, exist_ok=True)
    log_info(f"Folder created: {path}")


def move_file(src: str, dest: str):
    shutil.move(src, dest)
    log_info(f"Moved {src} → {dest}")


def rename_file(old: str, new: str):
    os.rename(old, new)
    log_info(f"Renamed {old} → {new}")


def list_files(path: str = ".") -> str:
    """List files in a directory."""
    try:
        items = os.listdir(path)
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        folders = [f for f in items if os.path.isdir(os.path.join(path, f))]
        result = f"In {path}:\nFolders: {', '.join(folders) or 'none'}\nFiles: {', '.join(files[:10]) or 'none'}"
        return result
    except Exception as e:
        return f"Could not list files: {e}"


def search_files(name: str, search_path: str = os.path.expanduser("~")) -> str:
    """Search for files by name."""
    try:
        matches = []
        for root, dirs, files in os.walk(search_path):
            for f in files:
                if name.lower() in f.lower():
                    matches.append(os.path.join(root, f))
            if len(matches) >= 5:
                break
        if matches:
            return "Found:\n" + "\n".join(matches[:5])
        return f"No files found with name '{name}' Boss."
    except Exception as e:
        return f"Search error: {e}"


def get_file_info(path: str) -> str:
    """Get file size, modified date, etc."""
    try:
        stat = os.stat(path)
        size = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"File: {path}\nSize: {size:.1f} KB\nModified: {modified}"
    except Exception as e:
        return f"Cannot get file info: {e}"