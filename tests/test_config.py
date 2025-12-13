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
        # Mandatory fields
        vocabulary_iri="https://example.org/extra/",
        title="Extra Vocabulary",
        description="An extra vocabulary",
        created_date="2025-01-01",
        creator="Test Creator",
        repository="https://github.com/test/extra",
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
    """Test that config_version defaults to empty string (for pre-v1.0 detection)."""
    config = temp_config
    assert config.IDRANGES.config_version == ""


def test_config_version_from_file(datadir, temp_config):
    """Test config_version is read from file."""
    config = temp_config
    config.load_config(datadir / "idranges_with_scheme.toml")
    assert config.IDRANGES.config_version == "v1.0"


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


def test_optional_scheme_metadata_fields_defaults(datadir, temp_config):
    """Test optional scheme metadata fields default to empty strings when not present."""
    config = temp_config
    # Load config with mandatory fields but without optional metadata (valid_idranges.toml)
    config.load_config(datadir / VALID_CONFIG)

    vocab = config.IDRANGES.vocabs["myvocab"]

    # Optional scheme metadata fields should default to empty strings
    assert vocab.prefix == ""
    assert vocab.publisher == ""
    assert vocab.custodian == ""
    assert vocab.catalogue_pid == ""
    assert vocab.documentation == ""
    assert vocab.issue_tracker == ""
    assert vocab.helpdesk == ""
    assert vocab.homepage == ""
    assert vocab.conforms_to == ""

    # Mandatory fields should be filled (from valid_idranges.toml)
    assert vocab.vocabulary_iri != ""
    assert vocab.title != ""
    assert vocab.description != ""
    assert vocab.created_date != ""
    assert vocab.creator != ""
    assert vocab.repository != ""


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
    """Test that old config files without config_version still work.

    Pre-v1.0 configs lack config_version field, so it defaults to empty string.
    This allows detection of pre-v1.0 configs for upgrade workflows.
    """
    config = temp_config
    # valid_idranges.toml doesn't have config_version
    config.load_config(datadir / VALID_CONFIG)

    # Should default to "" (empty) for pre-v1.0 detection
    assert config.IDRANGES.config_version == ""
    # Rest should work normally
    assert config.IDRANGES.single_vocab is True
    assert "myvocab" in config.IDRANGES.vocabs


# === Tests for mandatory field validation ===


def test_mandatory_fields_validation_error(temp_config):
    """Test that missing mandatory fields raise ValidationError."""
    config = temp_config

    # Try to create a Vocab without mandatory fields
    with pytest.raises(ValidationError) as excinfo:
        config.Vocab(
            id_length=7,
            permanent_iri_part="https://example.org/",
            checks={},
            prefix_map={},
            # No mandatory scheme metadata fields provided
        )

    error_msg = str(excinfo.value)
    # Should list all missing mandatory fields
    assert "vocabulary_iri" in error_msg
    assert "title" in error_msg
    assert "description" in error_msg
    assert "created_date" in error_msg
    assert "creator" in error_msg
    assert "repository" in error_msg


def test_mandatory_fields_whitespace_only_rejected(temp_config):
    """Test that whitespace-only values for mandatory fields are rejected."""
    config = temp_config

    with pytest.raises(ValidationError) as excinfo:
        config.Vocab(
            id_length=7,
            permanent_iri_part="https://example.org/",
            checks={},
            prefix_map={},
            vocabulary_iri="   ",  # Whitespace only
            title="\t",  # Tab only
            description="\n",  # Newline only
            created_date="  ",
            creator="",
            repository="",
        )

    error_msg = str(excinfo.value)
    assert "Mandatory ConceptScheme fields are empty" in error_msg


def test_all_mandatory_fields_present_valid(temp_config):
    """Test that a Vocab with all mandatory fields is valid."""
    config = temp_config

    vocab = config.Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/",
        checks={},
        prefix_map={},
        vocabulary_iri="https://example.org/vocab/",
        title="Test Vocabulary",
        description="A test vocabulary",
        created_date="2025-01-01",
        creator="Test Author",
        repository="https://github.com/test/vocab",
    )

    assert vocab.vocabulary_iri == "https://example.org/vocab/"
    assert vocab.title == "Test Vocabulary"
    assert vocab.description == "A test vocabulary"
    assert vocab.created_date == "2025-01-01"
    assert vocab.creator == "Test Author"
    assert vocab.repository == "https://github.com/test/vocab"


def test_optional_fields_can_be_empty(temp_config):
    """Test that optional fields are allowed to be empty."""
    config = temp_config

    # Create vocab with only mandatory fields (optional fields will be empty)
    vocab = config.Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/",
        checks={},
        prefix_map={},
        vocabulary_iri="https://example.org/vocab/",
        title="Test Vocabulary",
        description="A test vocabulary",
        created_date="2025-01-01",
        creator="Test Author",
        repository="https://github.com/test/vocab",
        # Optional fields explicitly empty
        prefix="",
        publisher="",
        custodian="",
        catalogue_pid="",
        documentation="",
        issue_tracker="",
        helpdesk="",
        homepage="",
        conforms_to="",
    )

    # All optional fields should be empty strings
    assert vocab.prefix == ""
    assert vocab.publisher == ""
    assert vocab.custodian == ""
    assert vocab.catalogue_pid == ""
    assert vocab.documentation == ""
    assert vocab.issue_tracker == ""
    assert vocab.helpdesk == ""
    assert vocab.homepage == ""
    assert vocab.conforms_to == ""


# === Tests for IdrangeItem name field ===


def test_idrange_item_with_name(temp_config):
    """Test IdrangeItem accepts optional name field."""
    config = temp_config
    ri = config.IdrangeItem(
        first_id=1,
        last_id=10,
        gh_name="testuser",
        name="Test User",
        orcid="0000-0001-2345-6789",
    )
    assert ri.name == "Test User"
    assert ri.gh_name == "testuser"


def test_idrange_item_name_empty_default(temp_config):
    """Test IdrangeItem name defaults to empty string."""
    config = temp_config
    ri = config.IdrangeItem(first_id=1, last_id=10, gh_name="testuser")
    assert ri.name == ""


def test_idrange_item_name_from_config_file(datadir, temp_config):
    """Test name field is read from config file."""
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)

    vocab = config.IDRANGES.vocabs["myvocab"]
    # First id_range has name field
    assert vocab.id_range[0].name == "Sofia Garcia"
    # Second id_range does not have name field
    assert vocab.id_range[1].name == ""
    # Third id_range has name field
    assert vocab.id_range[2].name == "Anonymous Contributor"


# === Tests for provenance_url_template validation ===


def test_provenance_url_template_valid(temp_config):
    """Test that valid provenance_url_template is accepted."""
    config = temp_config

    vocab = config.Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/",
        checks={},
        prefix_map={},
        vocabulary_iri="https://example.org/vocab/",
        title="Test Vocabulary",
        description="A test vocabulary",
        created_date="2025-01-01",
        creator="Test Author",
        repository="https://github.com/test/vocab",
        provenance_url_template="https://gitlab.com/org/repo/-/blame/{{ version }}/vocabularies/{{ vocab_name }}/{{ entity_id }}.ttl",
    )

    assert "{{ entity_id }}" in vocab.provenance_url_template


def test_provenance_url_template_invalid_missing_entity_id(temp_config):
    """Test that provenance_url_template without entity_id is rejected."""
    config = temp_config

    with pytest.raises(ValidationError) as excinfo:
        config.Vocab(
            id_length=7,
            permanent_iri_part="https://example.org/",
            checks={},
            prefix_map={},
            vocabulary_iri="https://example.org/vocab/",
            title="Test Vocabulary",
            description="A test vocabulary",
            created_date="2025-01-01",
            creator="Test Author",
            repository="https://github.com/test/vocab",
            provenance_url_template="https://example.com/{{ vocab_name }}.ttl",  # Missing entity_id
        )

    error_msg = str(excinfo.value)
    assert "provenance_url_template must contain '{{ entity_id }}'" in error_msg


def test_provenance_url_template_empty_allowed(temp_config):
    """Test that empty provenance_url_template is allowed."""
    config = temp_config

    vocab = config.Vocab(
        id_length=7,
        permanent_iri_part="https://example.org/",
        checks={},
        prefix_map={},
        vocabulary_iri="https://example.org/vocab/",
        title="Test Vocabulary",
        description="A test vocabulary",
        created_date="2025-01-01",
        creator="Test Author",
        repository="https://github.com/test/vocab",
        provenance_url_template="",  # Empty is OK
    )

    assert vocab.provenance_url_template == ""
