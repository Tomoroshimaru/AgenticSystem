"""
Clean Python cache files
"""
import os
import shutil
from pathlib import Path

def clean_pycache(root_dir):
    """Remove all __pycache__ directories and .pyc files"""
    root = Path(root_dir)
    
    # Remove __pycache__ directories
    for pycache_dir in root.rglob("__pycache__"):
        print(f"Removing: {pycache_dir}")
        shutil.rmtree(pycache_dir, ignore_errors=True)
    
    # Remove .pyc files
    for pyc_file in root.rglob("*.pyc"):
        print(f"Removing: {pyc_file}")
        pyc_file.unlink(missing_ok=True)
    
    print("\n✅ Cache cleaned!")

if __name__ == "__main__":
    clean_pycache(Path(__file__).parent)
