"""Tests for voc4cat.config module."""

import logging

import pytest
from pydantic import ValidationError

VALID_CONFIG = "valid_idranges.toml"


def test_import(datadir, caplog, temp_config):
    """Standard case of valid jdranges.toml."""
    # default config available
    config = temp_config
    assert config.IDRANGES.single_vocab is False
    assert config.IDRANGES.vocabs == {}
    assert config.IDRANGES.default_config is True

    # load a valid config
    fpath = datadir / VALID_CONFIG
    with caplog.at_level(logging.DEBUG):
        config.load_config(fpath)
    assert f"Config loaded from: {fpath}" in caplog.text

    assert config.IDRANGES.single_vocab is True
    assert config.IDRANGES.default_config is False
    assert len(config.IDRANGES.vocabs) == 1
    assert "myvocab" in config.IDRANGES.vocabs
    assert len(config.IDRANGES.vocabs["myvocab"].id_range) == 3  # noqa: PLR2004


def test_non_exisiting_config_file(tmp_path, caplog, temp_config):
    """Test for non-existing path to config which initializes defaults"""
    config = temp_config
    fpath = tmp_path / "does-not-exist.toml"
    with caplog.at_level(logging.WARNING):
        config.load_config(config_file=fpath)
    assert f'Configuration file "{fpath}" not found.' in caplog.text

    assert config.IDRANGES.single_vocab is False
    assert config.IDRANGES.vocabs == {}
    assert config.IDRANGES.default_config is True


def test_overlapping_idranges(datadir, temp_config):
    """Test for non-existing path to config which initializes defaults"""
    config = temp_config

    # load a valid config
    config.load_config(datadir / VALID_CONFIG)

    overlapping_idrange = config.IdrangeItem(first_id=8, last_id=12, gh_name="overlap")
    config.IDRANGES.vocabs["myvocab"].id_range.append(overlapping_idrange)

    with pytest.raises(ValidationError, match="Overlapping ID ranges for IDs 8-12."):
        # pydantic does not automatically re-validate on attribute change.
        # We call load_config to trigger revalidation.
        config.load_config(config=config.IDRANGES)


def test_single_vocab_consistency(datadir, temp_config):
    """Test consistency check for single_vocab=True."""
    config = temp_config

    # load a valid config
    config.load_config(datadir / VALID_CONFIG)
    extra_vocab = config.Vocab(
        id_length=5,
        permanent_iri_part="https://example.org",
        checks={},
        prefix_map={},
        id_range=[{"first_id": 1, "last_id": 2, "gh_name": "otto"}],
    )
    config.IDRANGES.vocabs["another_vocab"] = extra_vocab

    assert config.IDRANGES.single_vocab is True
    with pytest.raises(
        ValidationError,
        match='Inconsistent config: "single_vocab" is true but multiple vocabularies are found.',
    ):
        config.load_config(config=config.IDRANGES)


def test_idrange_item_validation(datadir, temp_config):
    """Test for custom vlidators in config.IdrangeItem"""
    config = temp_config

    with pytest.raises(ValidationError) as excinfo:
        _bad_ids = config.IdrangeItem(first_id=2, last_id=2, gh_name="no-range")

    assert "last_id (2) must be greater than first_id (2)." in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        _missing_name = config.IdrangeItem(first_id=1, last_id=2, gh_name="")

    assert "ID range requires a GitHub name or an ORCID (range: 1-2)." in str(
        excinfo.value
    )
