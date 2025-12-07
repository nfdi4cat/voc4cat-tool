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
    assert len(config.IDRANGES.vocabs["myvocab"].id_range) == 3


def test_non_existing_config_file(tmp_path, caplog, temp_config):
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


@pytest.mark.parametrize("gh_name", ["nobody", "NoBody", "no-body", "nobody-02"])
def test_gh_name_valid(temp_config, gh_name):
    """Test valid github names (issue193)"""
    config = temp_config
    ri = config.IdrangeItem(first_id=1, last_id=2, gh_name=gh_name)
    assert ri.gh_name == gh_name


@pytest.mark.parametrize("gh_name", ["", "-02"])
def test_gh_name_invalid(temp_config, gh_name):
    """Test invalid github names (issue193)"""
    config = temp_config
    with pytest.raises(ValidationError):
        config.IdrangeItem(first_id=1, last_id=2, gh_name=gh_name)


# === Tests for config_version and scheme metadata fields ===


def test_config_version_default(temp_config):
    """Test that config_version defaults to '1.0'."""
    config = temp_config
    assert config.IDRANGES.config_version == "1.0"


def test_config_version_from_file(datadir, temp_config):
    """Test config_version is read from file."""
    config = temp_config
    config.load_config(datadir / "idranges_with_scheme.toml")
    assert config.IDRANGES.config_version == "1.0"


def test_scheme_metadata_fields_all_present(datadir, temp_config):
    """Test all scheme metadata fields are read correctly."""
    config = temp_config
    config.load_config(datadir / "idranges_with_scheme.toml")

    vocab = config.IDRANGES.vocabs["myvocab"]

    assert vocab.vocabulary_iri == "https://example.org/vocab/"
    assert vocab.prefix == "ex"
    assert vocab.title == "Test Vocabulary"
    assert vocab.description == "A test vocabulary for unit tests."
    assert vocab.created_date == "2025-01-15"
    assert "Alice Smith" in vocab.creator
    assert "https://orcid.org/0000-0001-2345-6789" in vocab.creator
    assert "Example Organization" in vocab.publisher
    assert "Bob Jones" in vocab.custodian
    assert vocab.catalogue_pid == "https://doi.org/10.1234/example"
    assert vocab.documentation == "https://example.org/docs"
    assert vocab.issue_tracker == "https://github.com/example/vocab/issues"
    assert vocab.helpdesk == "https://example.org/helpdesk"
    assert vocab.repository == "https://github.com/example/vocab"
    assert vocab.homepage == "https://example.org"
    assert vocab.conforms_to == "https://w3id.org/profile/vocpub"


def test_scheme_metadata_fields_defaults(datadir, temp_config):
    """Test scheme metadata fields default to empty strings when not present."""
    config = temp_config
    # Load config without scheme metadata (valid_idranges.toml)
    config.load_config(datadir / VALID_CONFIG)

    vocab = config.IDRANGES.vocabs["myvocab"]

    # All scheme metadata fields should be empty strings
    assert vocab.vocabulary_iri == ""
    assert vocab.prefix == ""
    assert vocab.title == ""
    assert vocab.description == ""
    assert vocab.created_date == ""
    assert vocab.creator == ""
    assert vocab.publisher == ""
    assert vocab.custodian == ""
    assert vocab.catalogue_pid == ""
    assert vocab.documentation == ""
    assert vocab.issue_tracker == ""
    assert vocab.helpdesk == ""
    assert vocab.repository == ""
    assert vocab.homepage == ""
    assert vocab.conforms_to == ""


def test_multiline_creator_field(datadir, temp_config):
    """Test multi-line creator field parsing."""
    config = temp_config
    config.load_config(datadir / "idranges_with_scheme.toml")

    vocab = config.IDRANGES.vocabs["myvocab"]

    # Creator should contain multiple lines
    lines = [line.strip() for line in vocab.creator.strip().split("\n") if line.strip()]
    assert len(lines) == 2
    assert "Alice Smith" in lines[0]
    assert "Example Org" in lines[1]


def test_backward_compatibility_no_config_version(datadir, temp_config):
    """Test that old config files without config_version still work."""
    config = temp_config
    # valid_idranges.toml doesn't have config_version
    config.load_config(datadir / VALID_CONFIG)

    # Should default to "1.0"
    assert config.IDRANGES.config_version == "1.0"
    # Rest should work normally
    assert config.IDRANGES.single_vocab is True
    assert "myvocab" in config.IDRANGES.vocabs
