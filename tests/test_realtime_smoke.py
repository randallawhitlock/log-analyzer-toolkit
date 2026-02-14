from unittest.mock import MagicMock

from backend.api.realtime import LogTailer


def test_realtime_import_and_init():
    """Smoke test to verify realtime module imports and LogTailer inits."""
    mock_ws = MagicMock()
    tailer = LogTailer(mock_ws, "test.log")
    assert tailer.file_path.name == "test.log"
    assert tailer.filter_pattern is None
