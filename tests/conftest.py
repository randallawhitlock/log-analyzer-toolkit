import warnings


def pytest_configure(config):
    """Configure pytest environment."""
    # Suppress NotOpenSSLWarning from urllib3
    try:
        from urllib3.exceptions import NotOpenSSLWarning

        warnings.simplefilter("ignore", NotOpenSSLWarning)
    except ImportError:
        pass
