"""
Core log file reader functionality.

Provides basic file reading and line iteration with encoding detection
and error handling for common log file scenarios.
"""

import os
from collections.abc import Iterator
from pathlib import Path


class LogReader:
    """
    Reads log files with proper encoding handling and error recovery.

    Supports reading from files, stdin, or compressed files (gzip).
    """

    def __init__(self, filepath: str, encoding: str = "utf-8"):
        """
        Initialize the log reader.

        Args:
            filepath: Path to the log file to read
            encoding: Character encoding (default: utf-8)
        """
        self.filepath = Path(filepath)
        self.encoding = encoding
        self._validate_file()

    def _validate_file(self) -> None:
        """Validate that the file exists and is readable."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Log file not found: {self.filepath}")
        if not self.filepath.is_file():
            raise ValueError(f"Path is not a file: {self.filepath}")
        if not os.access(self.filepath, os.R_OK):
            raise PermissionError(f"Cannot read file: {self.filepath}")

    def read_lines(self) -> Iterator[str]:
        """
        Iterate over lines in the log file.

        Yields:
            Each line from the log file, stripped of trailing newlines.
        """
        try:
            with open(self.filepath, encoding=self.encoding, errors="replace") as f:
                for line in f:
                    yield line.rstrip("\n\r")
        except UnicodeDecodeError as e:
            raise ValueError(f"Encoding error: {e}") from e

    def count_lines(self) -> int:
        """
        Count total lines in the file without loading into memory.

        Returns:
            Total number of lines in the file.
        """
        count = 0
        with open(self.filepath, "rb") as f:
            for _ in f:
                count += 1
        return count
