# -*- coding: utf-8 -*-
"""
Atomic JSON file operations for better data integrity and performance
"""

import os
import json
import tempfile
import shutil
try:
    import fcntl
except ImportError:
    # fcntl is not available on Windows
    fcntl = None
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional
import gzip
import threading

# Thread-local lock storage for per-file locking
_file_locks = threading.local()

def get_file_lock(filepath: str):
    """Get or create a lock for a specific file path"""
    if not hasattr(_file_locks, 'locks'):
        _file_locks.locks = {}
    
    if filepath not in _file_locks.locks:
        _file_locks.locks[filepath] = threading.RLock()
    
    return _file_locks.locks[filepath]

@contextmanager
def file_lock(filepath: str):
    """Context manager for file-level locking"""
    lock = get_file_lock(filepath)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

def atomic_write_json(filepath: str, data: Any, compress: bool = False, indent: int = 2) -> bool:
    """
    Atomically write JSON data to file with optional compression
    
    Args:
        filepath: Target file path
        data: Data to write
        compress: Whether to compress with gzip
        indent: JSON indentation (None for compact)
    
    Returns:
        bool: Success status
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with file_lock(filepath):
            # Write to temporary file first
            temp_dir = os.path.dirname(filepath)
            with tempfile.NamedTemporaryFile(
                mode='wb' if compress else 'w', 
                dir=temp_dir, 
                delete=False,
                suffix='.tmp',
                encoding=None if compress else 'utf-8'
            ) as tmp_file:
                
                if compress:
                    # Compress JSON data
                    json_bytes = json.dumps(data, ensure_ascii=False, indent=indent).encode('utf-8')
                    with gzip.GzipFile(fileobj=tmp_file, mode='wb') as gz:
                        gz.write(json_bytes)
                else:
                    # Regular JSON write
                    json.dump(data, tmp_file, ensure_ascii=False, indent=indent)
                
                tmp_filepath = tmp_file.name
            
            # Atomic rename - this is the key to atomicity
            shutil.move(tmp_filepath, filepath)
            
            return True
            
    except Exception as e:
        # Clean up temp file if it exists
        if 'tmp_filepath' in locals() and os.path.exists(tmp_filepath):
            try:
                os.unlink(tmp_filepath)
            except:
                pass
        print(f"❌ Atomic JSON write error for {filepath}: {e}")
        return False

def atomic_read_json(filepath: str, default: Any = None, compressed: bool = None) -> Any:
    """
    Atomically read JSON data from file with optional decompression
    
    Args:
        filepath: Source file path
        default: Default value if file doesn't exist
        compressed: Whether file is gzip compressed (auto-detect if None)
    
    Returns:
        Loaded data or default value
    """
    try:
        if not os.path.exists(filepath):
            return default
            
        with file_lock(filepath):
            # Auto-detect compression if not specified
            if compressed is None:
                with open(filepath, 'rb') as f:
                    # Check for gzip magic number
                    magic = f.read(2)
                    compressed = magic == b'\x1f\x8b'
            
            if compressed:
                # Read compressed JSON
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Read regular JSON
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"⚠️ JSON read error for {filepath}: {e}")
        return default
    except Exception as e:
        print(f"❌ Atomic JSON read error for {filepath}: {e}")
        return default

def atomic_update_json(filepath: str, update_func, default: Any = None, compress: bool = False) -> bool:
    """
    Atomically update JSON file using an update function
    
    Args:
        filepath: Target file path
        update_func: Function that takes current data and returns updated data
        default: Default value for new files
        compress: Whether to compress the output
        
    Returns:
        bool: Success status
    """
    try:
        with file_lock(filepath):
            # Read current data
            current_data = atomic_read_json(filepath, default)
            
            # Apply update function
            updated_data = update_func(current_data)
            
            # Write updated data atomically
            return atomic_write_json(filepath, updated_data, compress=compress)
            
    except Exception as e:
        print(f"❌ Atomic JSON update error for {filepath}: {e}")
        return False

def compress_json_file(filepath: str, remove_original: bool = True) -> bool:
    """
    Compress an existing JSON file using gzip
    
    Args:
        filepath: Path to JSON file
        remove_original: Whether to remove the original file
        
    Returns:
        bool: Success status
    """
    try:
        if not os.path.exists(filepath):
            return False
            
        # Read original data
        data = atomic_read_json(filepath)
        if data is None:
            return False
            
        # Write compressed version
        compressed_path = filepath + '.gz'
        success = atomic_write_json(compressed_path, data, compress=True)
        
        if success and remove_original:
            os.unlink(filepath)
            # Rename compressed file to original name
            shutil.move(compressed_path, filepath)
            
        return success
        
    except Exception as e:
        print(f"❌ JSON compression error for {filepath}: {e}")
        return False

def get_file_size_mb(filepath: str) -> float:
    """Get file size in MB"""
    try:
        if os.path.exists(filepath):
            return os.path.getsize(filepath) / (1024 * 1024)
        return 0.0
    except:
        return 0.0

def optimize_json_storage(directory: str, size_threshold_mb: float = 1.0) -> Dict[str, Any]:
    """
    Optimize JSON files in a directory by compressing large files
    
    Args:
        directory: Directory to scan
        size_threshold_mb: Minimum size in MB to trigger compression
        
    Returns:
        Dict with optimization results
    """
    results = {
        "files_processed": 0,
        "files_compressed": 0,
        "space_saved_mb": 0.0,
        "errors": []
    }
    
    try:
        if not os.path.exists(directory):
            return results
            
        for filename in os.listdir(directory):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(directory, filename)
            file_size = get_file_size_mb(filepath)
            results["files_processed"] += 1
            
            if file_size >= size_threshold_mb:
                original_size = file_size
                if compress_json_file(filepath):
                    new_size = get_file_size_mb(filepath)
                    results["files_compressed"] += 1
                    results["space_saved_mb"] += original_size - new_size
                else:
                    results["errors"].append(f"Failed to compress {filename}")
                    
    except Exception as e:
        results["errors"].append(f"Directory scan error: {e}")
        
    return results