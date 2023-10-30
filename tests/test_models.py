import datetime
import os
from unittest import mock

import pytest
from pydantic.error_wrappers import ValidationError
from rdflib import Graph
from voc4cat import config
from voc4cat.models import Concept, ConceptScheme, reset_curies

VALID_CONFIG = "valid_idranges.toml"


def test_reset_curies():
    """Test for voc4cat.models.reset_curies"""
    reset_curies({"ex": "https://example.org/"})
    assert "ex" in config.curies_converter.prefix_map
    assert "ex" in [prefix for prefix, _url in config.namespace_manager.namespaces()]

    # Test disallowed overwriting of CURIE
    config.load_config()
    new = {"skos": "https://example.org/SKOS/"}
    with pytest.raises(ValueError, match='Prefix "skos" is already used for'):
        reset_curies(new)


def test_check_uri_vs_config(datadir, temp_config):
    """
    Tests for pydantic root_validator voc4cat.models.check_uri_vs_config
    """
    # load a valid config
    config = temp_config
    config.load_config(datadir / VALID_CONFIG)

    # Concept IRI matching "permanent_iri_part" from config
    c = Concept(
        uri="https://example.org/0000010",
        pref_label="Thing X",
        definition="Fake def for 0000010",
        provenance="sofia-garcia",
        vocab_name="myvocab",
    )
    assert c.pref_label == "Thing X"

    # Concept IRI not matching "permanent_iri_part" from config
    with pytest.raises(ValidationError) as excinfo:
        c = Concept(
            uri="https://example.com/0000001",
            pref_label="Thing I",
            definition="Fake def for 0000001",
            vocab_name="myvocab",
        )
    assert (
        "Invalid IRI https://example.com/0000001 - It must start with https://example.org/"
        in str(excinfo.value)
    )

    # ID part of concept IRI not matching "permanent_iri_part" from config
    with pytest.raises(ValidationError) as excinfo:
        c = Concept(
            uri="https://example.org/a000005",
            pref_label="Thing V",
            definition="Fake def for 000005",
            vocab_name="myvocab",
        )
    assert (
        'Invalid ID part "a000005" in IRI https://example.org/a000005. The ID part may only contain digits.'
        in str(excinfo.value)
    )

    # ID part of concept IRI not matching "permanent_iri_part" from config
    with pytest.raises(ValidationError) as excinfo:
        c = Concept(
            uri="https://example.org/000005",
            pref_label="Thing V",
            definition="Fake def for 000005",
            vocab_name="myvocab",
        )
    assert (
        "ID part of https://example.org/000005 is not matching the configured pattern of 7 digits."
        in str(excinfo.value)
    )


# === From here on: "old" tests from rdflib.vocexcel ===


@mock.patch.dict(os.environ, clear=True)  # required to hide gh-action environment vars
def test_vocabulary_valid():
    cs = ConceptScheme(
        uri="https://linked.data.gov.au/def/borehole-start-point",
        title="Borehole Start Point",
        description="Indicates the nature of the borehole start point location",
        created="2020-04-02",
        modified="2020-04-04",
        creator="GSQ",
        publisher="GSQ",
        version="1.0",
        provenance="Derived from the 2011-09 version of CGI Borehole start point list",
        custodian="Vance Kelly",
        pid="http://pid.geoscience.gov.au/dataset/ga/114541",
    )
    assert cs.modified == datetime.date(2020, 4, 4)
    assert cs.version == "1.0"


@mock.patch.dict(os.environ, {"CI": ""})
def test_vocabulary_valid_in_ci():
    cs = ConceptScheme(
        uri="https://linked.data.gov.au/def/borehole-start-point",
        title="Borehole Start Point",
        description="Indicates the nature of the borehole start point location",
        created="2020-04-02",
        modified="2020-04-04",
        creator="GSQ",
        publisher="GSQ",
        version="1.0",
        provenance="Derived from the 2011-09 version of CGI Borehole start point list",
        custodian="Vance Kelly",
        pid="http://pid.geoscience.gov.au/dataset/ga/114541",
    )
    assert cs.version == "automatic"


@mock.patch.dict(
    os.environ,
    {"CI": "", "VOC4CAT_VERSION": "v2023-08-15", "VOC4CAT_MODIFIED": "2023-08-15"},
)
def test_vocabulary_valid_modified_via_envvar():
    cs = ConceptScheme(
        uri="https://linked.data.gov.au/def/borehole-start-point",
        title="Borehole Start Point",
        description="Indicates the nature of the borehole start point location",
        created="2020-04-02",
        modified="2020-04-04",
        creator="GSQ",
        publisher="GSQ",
        version="1.0",
        provenance="Derived from the 2011-09 version of CGI Borehole start point list",
        custodian="Vance Kelly",
        pid="http://pid.geoscience.gov.au/dataset/ga/114541",
    )
    assert cs.modified == datetime.date(2023, 8, 15)
    assert cs.version == "v2023-08-15"


@mock.patch.dict(os.environ, {"CI": "", "VOC4CAT_VERSION": "v2023-08-15"})
def test_vocabulary_valid_version_via_envvar():
    cs = ConceptScheme(
        uri="https://linked.data.gov.au/def/borehole-start-point",
        title="Borehole Start Point",
        description="Indicates the nature of the borehole start point location",
        created="2020-04-02",
        modified="2020-04-04",
        creator="GSQ",
        publisher="GSQ",
        version="1.0",
        provenance="Derived from the 2011-09 version of CGI Borehole start point list",
        custodian="Vance Kelly",
        pid="http://pid.geoscience.gov.au/dataset/ga/114541",
    )
    assert cs.version == "v2023-08-15"


@mock.patch.dict(os.environ, {"CI": "", "VOC4CAT_VERSION": "v2023-08-15"})
def test_vocabulary_creator_orcid():
    cs = ConceptScheme(
        uri="https://linked.data.gov.au/def/borehole-start-point",
        title="Borehole Start Point",
        description="Indicates the nature of the borehole start point location",
        created="2020-04-02",
        modified="2020-04-04",
        creator="0000-0001-2345-6789",
        publisher="GSQ",
        version="1.0",
        provenance="Derived from the 2011-09 version of CGI Borehole start point list",
        custodian="Vance Kelly",
        pid="http://pid.geoscience.gov.au/dataset/ga/114541",
    )
    assert cs.creator == "https://orcid.org/0000-0001-2345-6789"


@mock.patch.dict(os.environ, {"CI": "", "VOC4CAT_VERSION": "v2023-08-15"})
def test_vocabulary_creator_invalid():
    with pytest.raises(
        ValidationError,
        match="Creator must be an ORCID or ROR ID or a string from the organisations list",
    ):
        ConceptScheme(
            uri="https://linked.data.gov.au/def/borehole-start-point",
            title="Borehole Start Point",
            description="Indicates the nature of the borehole start point location",
            created="2020-04-02",
            modified="2020-04-04",
            creator="abc",
            publisher="https://ror.org/04fa4r544",
            version="1.0",
            provenance="Derived from the 2011-09 version of CGI Borehole start point list",
            custodian="Vance Kelly",
            pid="http://pid.geoscience.gov.au/dataset/ga/114541",
        )


@mock.patch.dict(os.environ, {"CI": "", "VOC4CAT_VERSION": "2023-08-15"})
def test_vocabulary_invalid_version_via_envvar():
    with pytest.raises(
        ValidationError, match="Invalid environment variable VOC4CAT_VERSION"
    ):
        ConceptScheme(
            uri="https://linked.data.gov.au/def/borehole-start-point",
            title="Borehole Start Point",
            description="Indicates the nature of the borehole start point location",
            created="2020-04-02",
            modified="2020-04-04",
            creator="GSQ",
            publisher="GSQ",
            version="1.0",
            provenance="Derived from the 2011-09 version of CGI Borehole start point list",
            custodian="Vance Kelly",
            pid="http://pid.geoscience.gov.au/dataset/ga/114541",
        )


def test_vocabulary_invalid_uri():
    with pytest.raises(ValidationError):
        ConceptScheme(
            uri="ftp://linked.data.gov.au/def/borehole-start-point",
            title="Borehole Start Point",
            description="Indicates the nature of the borehole start point location",
            created="2020-04-02",
            modified=None,
            creator="GSQ",
            publisher="GSQ",
            version="",
            provenance="Derived from the 2011-09 version of CGI Borehole start point list",
            custodian="Vance Kelly",
            pid="http://pid.geoscience.gov.au/dataset/ga/114541",
        )


def test_vocabulary_invalid_created_date():
    with pytest.raises(ValidationError):
        ConceptScheme(
            uri="https://linked.data.gov.au/def/borehole-start-point",
            title="Borehole Start Point",
            description="Indicates the nature of the borehole start point location",
            created="2020-04",
            modified="2020-04-04",
            creator="GSQ",
            publisher="GSQ",
            version="",
            provenance="Derived from the 2011-09 version of CGI Borehole start point list",
            custodian="Vance Kelly",
            pid="http://pid.geoscience.gov.au/dataset/ga/114541",
        )


def test_vocabulary_invalid_publisher():
    with pytest.raises(ValidationError):
        ConceptScheme(
            uri="https://linked.data.gov.au/def/borehole-start-point",
            title="Borehole Start Point",
            description="Indicates the nature of the borehole start point location",
            created="2020-04-02",
            modified="2020-04-04",
            creator="GSQ",
            publisher="WHO",
            version="",
            provenance="Derived from the 2011-09 version of CGI Borehole start point list",
            custodian="Vance Kelly",
            pid="http://pid.geoscience.gov.au/dataset/ga/114541",
        )


def test_concept():
    c = Concept(
        uri="https://example.com/thing/x",
        pref_label="Thing X",
        definition="Fake def for Thing X",
        children=["https://example.com/thing/y", "https://example.com/thing/z"],
        close_match=[
            "https://example.com/thing/other",
            "https://example.com/thing/otherother",
        ],
    )
    actual = c.to_graph()
    expected = Graph().parse(
        data="""@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix dcterms: <http://purl.org/dc/terms/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<https://example.com/thing/y> skos:broader <https://example.com/thing/x> .
<https://example.com/thing/z> skos:broader <https://example.com/thing/x> .
<https://example.com/thing/x> a skos:Concept ;
    skos:closeMatch <https://example.com/thing/other>, <https://example.com/thing/otherother> ;
    skos:definition "Fake def for Thing X"@en ;
    skos:narrower <https://example.com/thing/y>, <https://example.com/thing/z> ;
    dcterms:identifier "x"^^xsd:token ;
    skos:prefLabel "Thing X"@en ."""
    )

    assert actual.isomorphic(expected)


def test_concept_iri():
    # this is testing that children list elements are IRIs, not just ordinary strings
    with pytest.raises(ValidationError):
        Concept(
            uri="https://example.com/thing/x",
            pref_label="Thing X",
            definition="Fake def for Thing X",
            children=["broken iri", "http://example.com/working-iri"],  # non-IRI string
        )

    with pytest.raises(ValidationError):
        Concept(
            uri="https://example.com/thing/x",
            pref_label="Thing X",
            definition="Fake def for Thing X",
            children=[
                "ftp://example.com/working-iri",
                "http://example.com/working-iri",
            ],  # IRI starts ftp
        )

    with pytest.raises(ValidationError):
        Concept(
            uri="https://example.com/thing/x",
            pref_label="Thing X",
            definition="Fake def for Thing X",
            children=[
                "http://example.com/ working-iri",
                "http://example.com/working-iri",
            ],  # space in IRI
        )

    # valid children, invalid related_match
    with pytest.raises(ValidationError):
        Concept(
            uri="https://example.com/thing/x",
            pref_label="Thing X",
            definition="Fake def for Thing X",
            related_match=[
                "http://example.com/working-iri/rm/1",
                "http://example.com/working-iri/rm/ 2",  # space
                "ftp://example.com/working-iri/rm/3",  # starts ftp
            ],
            children=[
                "http://example.com/working-iri/c/1",
                "http://example.com/working-iri/c/2",
            ],
        )
