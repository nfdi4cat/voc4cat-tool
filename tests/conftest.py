# Common pytest fixtures for all test modules
import pytest


@pytest.fixture(scope="session")
def datadir():
    """DATADIR as a LocalPath"""
    from pathlib import Path

    return Path(__file__).resolve().parent / "data"


@pytest.fixture()
def temp_config():
    """
    Provides a temporary config that can be safely changed in test functions.

    After the test the config will be reset to default.
    """
    from voc4cat import config

    yield config

    # Reset the globally changed config to default.
    config.load_config()
