from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef, compare
from rdflib.namespace import DCTERMS, SKOS
from vocexcel import convert
from vocexcel.utils import ConversionError


def test_empty_template():
    assert Path(
        Path(__file__).parent.parent / "templates" / "VocExcel-template_043.xlsx"
    ).is_file()
    with pytest.raises(ConversionError) as e:
        convert.excel_to_rdf(
            Path(__file__).parent.parent / "templates" / "VocExcel-template_043.xlsx",
            output_type="file",
        )
    assert "7 validation errors for ConceptScheme" in str(e)


def test_simple():
    g = convert.excel_to_rdf(
        Path(__file__).parent / "043_simple_valid.xlsx", output_type="graph"
    )
    assert len(g) == 142
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
    # tidy up
    # Path(Path(__file__).parent / "043_simple_valid.ttl").unlink(missing_ok=True)


def test_exhaustive_template_is_isomorphic():
    g1 = Graph().parse(
        Path(__file__).parent / "040_exhaustive_example_perfect_output.ttl"
    )
    g2 = convert.excel_to_rdf(
        Path(__file__).parent / "043_exhaustive_example.xlsx", output_type="graph"
    )
    assert compare.isomorphic(g1, g2), "Graphs are not Isomorphic"


def test_rdf_to_excel():
    g1 = Graph().parse(
        Path(__file__).parent / "040_exhaustive_example_perfect_output.ttl"
    )
    convert.rdf_to_excel(
        Path(__file__).parent / "040_exhaustive_example_perfect_output.ttl",
    )
    g2 = convert.excel_to_rdf(
        Path(__file__).parent / "040_exhaustive_example_perfect_output.xlsx",
        output_type="graph",
    )
    # clean up file
    Path(Path(__file__).parent / "040_exhaustive_example_perfect_output.xlsx").unlink(
        missing_ok=True
    )
    assert compare.isomorphic(g1, g2), "Graphs are not Isomorphic"
