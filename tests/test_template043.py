import os
from pathlib import Path
from unittest import mock

import pytest
import voc4cat
from rdflib import Graph, Literal, URIRef, compare
from rdflib.namespace import DCTERMS, SKOS
from voc4cat import convert
from voc4cat.utils import ConversionError


def test_empty_template():
    test_file = Path(voc4cat.__file__).parent / "blank_043.xlsx"
    assert test_file.is_file()
    with pytest.raises(ConversionError) as e:
        convert.excel_to_rdf(
            test_file,
            output_type="file",
        )
    assert "9 validation errors for ConceptScheme" in str(e)


def test_simple():
    g = convert.excel_to_rdf(
        Path(__file__).parent / "templ_versions" / "043_simple_valid.xlsx",
        output_type="graph",
    )
    assert len(g) == 142  # noqa: PLR2004
    assert (
        URIRef(
            "http://resource.geosciml.org/classifierscheme/cgi/2016.01/particletype"
        ),
        SKOS.prefLabel,
        Literal("Particle Type", lang="en"),
    ) in g, "PrefLabel for vocab is not correct"
    assert (
        URIRef("http://resource.geosciml.org/classifier/cgi/particletype/bioclast"),
        DCTERMS.provenance,
        Literal("NADM SLTTs 2004", lang="en"),
    ) in g, "Provenance for vocab is not correct"


@mock.patch.dict(os.environ, clear=True)  # required to hide gh-action environment vars
def test_exhaustive_template_is_isomorphic():
    g1 = Graph().parse(
        Path(__file__).parent
        / "templ_versions"
        / "043_exhaustive_example_perfect_output.ttl"
    )
    g2 = convert.excel_to_rdf(
        Path(__file__).parent / "templ_versions" / "043_exhaustive_example.xlsx",
        output_type="graph",
    )
    assert compare.isomorphic(g1, g2), "Graphs are not Isomorphic"


@mock.patch.dict(os.environ, clear=True)  # required to hide gh-action environment vars
def test_rdf_to_excel():
    g1 = Graph().parse(
        Path(__file__).parent
        / "templ_versions"
        / "043_exhaustive_example_perfect_output.ttl"
    )
    convert.rdf_to_excel(
        Path(__file__).parent
        / "templ_versions"
        / "043_exhaustive_example_perfect_output.ttl",
    )
    g2 = convert.excel_to_rdf(
        Path(__file__).parent
        / "templ_versions"
        / "043_exhaustive_example_perfect_output.xlsx",
        output_type="graph",
    )
    # clean up file
    (
        Path(__file__).parent
        / "templ_versions"
        / "043_exhaustive_example_perfect_output.xlsx"
    ).unlink(missing_ok=True)
    # to debug differences
    # in_both, in_first, in_second = compare.graph_diff(g1, g2)
    # print("\nOnly in 1st ==>\n", in_first.serialize(format="turtle"))
    # print("Only in 2nd ==>\n", in_second.serialize(format="turtle"))

    assert compare.isomorphic(g1, g2), "Graphs are not Isomorphic"
