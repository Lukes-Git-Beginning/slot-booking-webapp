# -*- coding: utf-8 -*-
"""
Cross-process file locking using fcntl (Linux) or msvcrt (Windows)

This module provides robust file locking that works across multiple processes,
solving the issue where threading.Lock only works within a single process.

In production with Gunicorn (4 workers), each worker is a separate process,
so we need OS-level file locks to prevent data corruption.
"""

import os
import time
import platform
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Import platform-specific locking mechanism
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False
    try:
        import msvcrt
        MSVCRT_AVAILABLE = True
    except ImportError:
        MSVCRT_AVAILABLE = False


class FileLockException(Exception):
    """Exception raised when file locking fails"""
    pass


class FileLock:
    """
    Cross-process file lock using OS-level primitives.

    Usage:
        with FileLock('/path/to/file.json'):
            # Critical section - only one process can be here
            data = load_json()
            modify(data)
            save_json(data)

    Features:
    - Works across multiple processes (Gunicorn workers)
    - Automatic lock release on exception
    - Configurable timeout
    - Platform-agnostic (Linux/Windows)
    """

    def __init__(
        self,
        filepath: str,
        timeout: float = 10.0,
        check_interval: float = 0.1
    ):
        """
        Initialize file lock.

        Args:
            filepath: Path to file to lock
            timeout: Maximum time to wait for lock (seconds)
            check_interval: Time between lock attempts (seconds)
        """
        self.filepath = filepath
        self.timeout = timeout
        self.check_interval = check_interval
        self.lock_filepath = f"{filepath}.lock"
        self.lock_file: Optional[int] = None

    def _acquire_fcntl(self) -> bool:
        """Acquire lock using fcntl (Linux/Unix)"""
        if not FCNTL_AVAILABLE:
            return False

        try:
            # Create lock file if it doesn't exist
            self.lock_file = os.open(
                self.lock_filepath,
                os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )

            # Try to acquire exclusive lock with timeout
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except (IOError, OSError) as e:
                    # Lock is held by another process
                    if time.time() - start_time >= self.timeout:
                        raise FileLockException(
                            f"Timeout waiting for lock on {self.filepath}"
                        )
                    time.sleep(self.check_interval)

        except Exception as e:
            if self.lock_file is not None:
                try:
                    os.close(self.lock_file)
                except:
                    pass
                self.lock_file = None
            raise FileLockException(f"Failed to acquire lock: {e}")

    def _release_fcntl(self) -> None:
        """Release lock acquired with fcntl"""
        if self.lock_file is not None:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                os.close(self.lock_file)
            except Exception as e:
                logger.warning(f"Error releasing fcntl lock: {e}")
            finally:
                self.lock_file = None

            # Clean up lock file
            try:
                if os.path.exists(self.lock_filepath):
                    os.unlink(self.lock_filepath)
            except:
                pass

    def _acquire_msvcrt(self) -> bool:
        """Acquire lock using msvcrt (Windows)"""
        if not MSVCRT_AVAILABLE:
            return False

        try:
            # Create lock file if it doesn't exist
            self.lock_file = os.open(
                self.lock_filepath,
                os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )

            # Try to acquire exclusive lock with timeout
            start_time = time.time()
            while True:
                try:
                    msvcrt.locking(
                        self.lock_file,
                        msvcrt.LK_NBLCK,
                        1
                    )
                    return True
                except OSError:
                    # Lock is held by another process
                    if time.time() - start_time >= self.timeout:
                        raise FileLockException(
                            f"Timeout waiting for lock on {self.filepath}"
                        )
                    time.sleep(self.check_interval)

        except Exception as e:
            if self.lock_file is not None:
                try:
                    os.close(self.lock_file)
                except:
                    pass
                self.lock_file = None
            raise FileLockException(f"Failed to acquire lock: {e}")

    def _release_msvcrt(self) -> None:
        """Release lock acquired with msvcrt"""
        if self.lock_file is not None:
            try:
                msvcrt.locking(
                    self.lock_file,
                    msvcrt.LK_UNLCK,
                    1
                )
                os.close(self.lock_file)
            except Exception as e:
                logger.warning(f"Error releasing msvcrt lock: {e}")
            finally:
                self.lock_file = None

            # Clean up lock file
            try:
                if os.path.exists(self.lock_filepath):
                    os.unlink(self.lock_filepath)
            except:
                pass

    def acquire(self) -> None:
        """Acquire the file lock"""
        # Try fcntl first (Linux/Unix)
        if FCNTL_AVAILABLE:
            self._acquire_fcntl()
            return

        # Fallback to msvcrt (Windows)
        if MSVCRT_AVAILABLE:
            self._acquire_msvcrt()
            return

        # No locking available - log warning
        logger.warning(
            f"No file locking mechanism available for {self.filepath}. "
            "Proceeding without lock (potential data corruption risk)."
        )

    def release(self) -> None:
        """Release the file lock"""
        if FCNTL_AVAILABLE:
            self._release_fcntl()
        elif MSVCRT_AVAILABLE:
            self._release_msvcrt()

    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False


@contextmanager
def file_lock(
    filepath: str,
    timeout: float = 10.0,
    check_interval: float = 0.1
):
    """
    Context manager for file locking.

    Usage:
        with file_lock('/path/to/data.json'):
            # Only one process can execute this block at a time
            data = load_json()
            modify(data)
            save_json(data)

    Args:
        filepath: Path to file to lock
        timeout: Maximum time to wait for lock (seconds)
        check_interval: Time between lock attempts (seconds)

    Raises:
        FileLockException: If lock cannot be acquired within timeout
    """
    lock = FileLock(filepath, timeout, check_interval)
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


def is_locking_available() -> bool:
    """Check if file locking is available on this platform"""
    return FCNTL_AVAILABLE or MSVCRT_AVAILABLE


def get_locking_mechanism() -> str:
    """Get the name of the locking mechanism being used"""
    if FCNTL_AVAILABLE:
        return "fcntl (Linux/Unix)"
    elif MSVCRT_AVAILABLE:
        return "msvcrt (Windows)"
    else:
        return "none (WARNING: No file locking available!)"
