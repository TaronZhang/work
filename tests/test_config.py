"""Tests for configuration loading."""

from src.config import config


def test_config_has_defaults():
    """Happy path: config loads with valid defaults."""
    assert config.host is not None
    assert config.port > 0
    assert config.max_content_length > 0


def test_config_upload_folder():
    """Happy path: upload folder path is set."""
    assert config.upload_folder is not None
    assert len(config.upload_folder) > 0


def test_config_auto_split_threshold():
    """Happy path: auto-split threshold is positive."""
    assert config.auto_split_threshold > 0
    assert config.auto_split_max_chars > 0
