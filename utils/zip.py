"""
Zip utilities for the daemon.
Defines:
- unzip_file(zip_path, extract_dir): Unzips a zip file to a directory.
- zip_folder(folder_path, zip_path): Zips a folder into a zip file.
"""
import zipfile
import os

def unzip_file(zip_path, extract_dir):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Failed to unzip file: {zip_path}. Reason: {e}")

import fnmatch

def zip_folder(folder_path, zip_path, include_patterns=None):
    """
    Zips a folder into a zip file.
    If include_patterns is provided (list of glob patterns), only files matching any pattern are included.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, folder_path)
                if include_patterns:
                    matched = any(fnmatch.fnmatch(file, pat) for pat in include_patterns)
                    if not matched:
                        continue
                zipf.write(abs_path, rel_path)
