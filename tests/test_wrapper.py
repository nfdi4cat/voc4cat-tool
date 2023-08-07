import logging

import pytest
from voc4cat.wrapper import build_docs

CS_SIMPLE = "concept-scheme-simple.xlsx"
CS_SIMPLE_TURTLE = "concept-scheme-simple.ttl"
CS_CYCLES = "concept-scheme-with-cycles.xlsx"
CS_CYCLES_TURTLE = "concept-scheme-with-cycles.ttl"
CS_CYCLES_INDENT = "concept-scheme-with-cycles_indent.xlsx"
CS_CYCLES_INDENT_IRI = "concept-scheme-with-cycles_indent_iri.xlsx"
CS_CYCLES_INDENT_DOT = "concept-scheme-with-cycles_indent-by-dot.xlsx"
CS_CYCLES_MULTI_LANG = "concept-scheme-with-cycles_multilang.xlsx"
CS_CYCLES_MULTI_LANG_IND = "concept-scheme-with-cycles_multilang_indent_iri.xlsx"


@pytest.mark.parametrize(
    "doc_builder",
    ["pylode", "ontospy"],
)
def test_build_docs(tmp_path, caplog, doc_builder):
    """Check handling of missing dir/file on documentation build."""
    with caplog.at_level(logging.INFO):
        exit_code = build_docs(tmp_path, tmp_path, doc_builder)
    assert exit_code == 1
    assert f"No turtle file(s) found to document in {tmp_path}" in caplog.text

    with caplog.at_level(logging.INFO):
        exit_code = build_docs(tmp_path / CS_CYCLES_TURTLE, tmp_path, doc_builder)
    assert exit_code == 1
    assert f"File/dir not found (for docs): {tmp_path/CS_CYCLES_TURTLE}" in caplog.text

    with caplog.at_level(logging.INFO):
        exit_code = build_docs(tmp_path / CS_CYCLES_TURTLE, tmp_path, "ontospy")
    assert exit_code == 1
    assert f"File/dir not found (for docs): {tmp_path/CS_CYCLES_TURTLE}" in caplog.text


def test_build_docs_unknown_builder(tmp_path, caplog):
    """Check handling of unknown documentation builder."""
    unknown_doc_builder = "123doc"
    with caplog.at_level(logging.INFO):
        exit_code = build_docs(tmp_path, tmp_path, unknown_doc_builder)
    assert exit_code == 1
    assert f"Unsupported document builder '{unknown_doc_builder}'." in caplog.text
