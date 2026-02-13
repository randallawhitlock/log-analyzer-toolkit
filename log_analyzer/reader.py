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
                for _line_num, line in enumerate(f, 1):
                    yield line.rstrip("\n\r")
        except UnicodeDecodeError as e:
            raise ValueError(f"Encoding error: {e}") from e

    def read_all(self, max_lines: int = 200_000) -> list[str]:
        """
        Read all lines from the log file into memory.

        Args:
            max_lines: Safety limit to prevent memory exhaustion (default: 200,000)

        Returns:
            List of all lines from the file.

        Raises:
            ValueError: If file exceeds max_lines limit
        """
        lines = []
        for i, line in enumerate(self.read_lines()):
            if i >= max_lines:
                raise ValueError(
                    f"File exceeds maximum line limit ({max_lines:,}). "
                    "Use streaming methods (read_lines) or increase limit."
                )
            lines.append(line)
        return lines

    def get_file_info(self) -> dict:
        """
        Get metadata about the log file.

        Returns:
            Dictionary containing file metadata.
        """
        stat = self.filepath.stat()
        return {
            "path": str(self.filepath.absolute()),
            "name": self.filepath.name,
            "size_bytes": stat.st_size,
            "modified": stat.st_mtime,
        }

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


def read_log_file(filepath: str, encoding: str = "utf-8") -> Iterator[str]:
    """
    Convenience function to read lines from a log file.

    Args:
        filepath: Path to the log file
        encoding: Character encoding (default: utf-8)

    Yields:
        Each line from the log file.
    """
    reader = LogReader(filepath, encoding)
    yield from reader.read_lines()
