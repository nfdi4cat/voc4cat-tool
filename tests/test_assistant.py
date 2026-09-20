"""Tests for the voc-assistant command line interface.

The command line layer is importable without the optional `assistant` extra,
so these tests run in CI. They drive it with a simple scoring backend instead
of sentence-transformers; the real backends are covered by the tests at the
end of this module, which are skipped when the extra is absent.
"""

import importlib.util
import shutil

import click
import pytest
from click.testing import CliRunner

from voc4cat import assistant

VOCAB = "myvocab.ttl"

CO_PRECIPITATION_1 = "https://example.org/0000001"
CO_PRECIPITATION_2 = "https://example.org/0000002"


class ExactLabelBackend:
    """Scores two labels 1.0 when they are equal and 0.0 otherwise.

    Definitions score below any sensible threshold, which is the situation
    issue #387 is about: an identical label whose definitions are worded
    independently.
    """

    def __init__(self, definition_score: float = 0.1) -> None:
        self.definition_score = definition_score

    def label_scores(self, sentences: list[str]) -> list[list[float]]:
        return [
            [1.0 if a.casefold() == b.casefold() else 0.0 for b in sentences]
            for a in sentences
        ]

    def definition_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [self.definition_score] * len(pairs)


@pytest.fixture
def vocab(datadir, tmp_path):
    """The duplicates fixture under a name that reads as a vocabulary name."""
    destination = tmp_path / VOCAB
    shutil.copy(datadir / "similarity-duplicates.ttl", destination)
    return destination


@pytest.fixture
def published(datadir, tmp_path):
    destination = tmp_path / "published.ttl"
    shutil.copy(datadir / "similarity-published.ttl", destination)
    return destination


@pytest.fixture
def idranges(tmp_path):
    def write(body: str = "", vocab_options: str = "") -> str:
        path = tmp_path / "idranges.toml"
        path.write_text(
            "single_vocab = true\n\n"
            "[vocabs.myvocab]\n"
            "id_length = 7\n"
            'permanent_iri_part = "https://example.org/"\n'
            'vocabulary_iri = "https://example.org/vocab/"\n'
            'title = "Test Vocabulary"\n'
            'description = "A vocabulary for testing"\n'
            'created_date = "2025-01-01"\n'
            'creator = "https://orcid.org/0000-0001-2345-6789 Test Creator"\n'
            'repository = "https://github.com/test/vocab"\n'
            f"{vocab_options}\n"
            "[vocabs.myvocab.checks]\n"
            "allow_delete = false\n\n"
            "[vocabs.myvocab.prefix_map]\n"
            'ex = "https://example.org/"\n\n' + body,
            encoding="utf-8",
        )
        return str(path)

    return write


@pytest.fixture
def run(monkeypatch):
    """Invoke the CLI with a backend that needs no model."""

    def invoke(args, backend=None):
        monkeypatch.setattr(
            assistant,
            "build_backend",
            lambda _method: backend or ExactLabelBackend(),
        )
        return CliRunner().invoke(assistant.cli, args, catch_exceptions=False)

    return invoke


def report_of(result, path):
    assert result.exit_code == 0, result.output
    return path.read_text(encoding="utf-8")


# === check ===


def test_check_reports_two_concepts_sharing_a_label(vocab, tmp_path, run):
    """The case from issue #387, end to end through the command line."""
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--output", str(output)])

    report = report_of(result, output)
    assert "0000001" in report
    assert "0000002" in report
    assert "co-precipitation" in report


def test_check_writes_a_default_report_name(vocab, tmp_path, run, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = run(["check", str(vocab), "--method", "levenshtein"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "check_report_levenshtein.md").exists()


def test_check_without_alt_labels_ignores_an_alt_label_match(vocab, tmp_path, run):
    """0000004 carries "co-precipitation" as an alt label only."""
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--no-alt-labels", "--output", str(output)])

    assert "0000004" not in report_of(result, output)


def test_check_with_alt_labels_finds_an_alt_label_match(vocab, tmp_path, run):
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--output", str(output)])

    assert "0000004" in report_of(result, output)


def test_a_certain_threshold_below_the_label_threshold_is_refused(vocab, tmp_path, run):
    result = run(
        [
            "check",
            str(vocab),
            "--threshold-labels",
            "0.9",
            "--threshold-labels-certain",
            "0.5",
            "--output",
            str(tmp_path / "report.md"),
        ]
    )

    assert result.exit_code != 0
    assert "threshold-labels-certain" in result.output


# === compare ===


def test_compare_reports_an_addition_that_duplicates_a_published_concept(
    vocab, published, tmp_path, run
):
    """Regression for the guard that made `compare` skip every concept.

    0000002 is new and carries the same label as the published 0000001.
    """
    output = tmp_path / "report.md"

    result = run(["compare", str(published), str(vocab), "--output", str(output)])

    report = report_of(result, output)
    assert "0000002" in report
    assert "0000001" in report


def test_compare_ignores_a_pair_of_concepts_that_were_both_published(
    published, tmp_path, run, datadir
):
    """Nothing was added, so there is nothing to report."""
    unchanged = tmp_path / "myvocab.ttl"
    shutil.copy(datadir / "similarity-published.ttl", unchanged)
    output = tmp_path / "report.md"

    result = run(["compare", str(published), str(unchanged), "--output", str(output)])

    assert "No similarities found." in report_of(result, output)


# === accepted similarities ===


ACCEPTED = (
    "[[vocabs.myvocab.accepted_similarity]]\n"
    'concepts = ["ex:0000001", "ex:0000002"]\n'
    'reason = "Distinct processes that share a label."\n'
)


def test_an_accepted_pair_is_moved_out_of_the_findings(vocab, tmp_path, run, idranges):
    output = tmp_path / "report.md"

    result = run(
        [
            "check",
            str(vocab),
            "--config",
            idranges(ACCEPTED),
            "--output",
            str(output),
        ]
    )

    report = report_of(result, output)
    assert "## Accepted similarities" in report
    assert "Distinct processes that share a label." in report


def test_accepted_pairs_can_be_hidden(vocab, tmp_path, run, idranges):
    output = tmp_path / "report.md"

    result = run(
        [
            "check",
            str(vocab),
            "--config",
            idranges(ACCEPTED),
            "--hide-accepted",
            "--output",
            str(output),
        ]
    )

    assert "## Accepted similarities" not in report_of(result, output)


def test_an_entry_naming_an_unknown_concept_is_reported(vocab, tmp_path, run, idranges):
    body = (
        "[[vocabs.myvocab.accepted_similarity]]\n"
        'concepts = ["ex:0000001", "ex:9999999"]\n'
        'reason = "Typo in the ID."\n'
    )
    output = tmp_path / "report.md"

    result = run(
        ["check", str(vocab), "--config", idranges(body), "--output", str(output)]
    )

    report = report_of(result, output)
    assert "## Unused accepted-similarity entries" in report
    assert "unknown concept" in report


def test_a_missing_config_file_is_a_warning_not_an_error(vocab, tmp_path, run):
    output = tmp_path / "report.md"

    result = run(
        [
            "check",
            str(vocab),
            "--config",
            str(tmp_path / "absent.toml"),
            "--output",
            str(output),
        ]
    )

    assert result.exit_code == 0, result.output
    assert output.exists()


def test_concepts_link_to_the_configured_documentation_url(
    vocab, tmp_path, run, idranges
):
    config = idranges(
        vocab_options=(
            'concept_url_template = "https://docs.example.org/#{{ entity_id }}"\n'
        )
    )
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--config", config, "--output", str(output)])

    assert "https://docs.example.org/#0000001" in report_of(result, output)


def test_concepts_link_to_their_iri_without_a_template(vocab, tmp_path, run):
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--output", str(output)])

    assert f"({CO_PRECIPITATION_1})" in report_of(result, output)


# === The scoring backends, which need the optional extra ===


@pytest.fixture
def sbert_backend():
    pytest.importorskip("sentence_transformers")
    return assistant.build_backend("sbert")


@pytest.fixture
def levenshtein_backend():
    pytest.importorskip("Levenshtein")
    return assistant.build_backend("levenshtein")


def test_levenshtein_scores_an_orthographic_variant_highly(levenshtein_backend):
    scores = levenshtein_backend.label_scores(["co-precipitation", "coprecipitation"])

    assert scores[0][1] > 0.9


def test_levenshtein_normalises_case_and_hyphens(levenshtein_backend):
    scores = levenshtein_backend.label_scores(["Co-Precipitation", "co precipitation"])

    assert scores[0][1] == 1.0


def test_sbert_scores_an_identical_label_as_identical(sbert_backend):
    scores = sbert_backend.label_scores(["co-precipitation", "co-precipitation"])

    assert scores[0][1] == pytest.approx(1.0, abs=1e-4)


def test_sbert_scores_definition_pairs(sbert_backend):
    scores = sbert_backend.definition_scores(
        [("A cat sits on the mat.", "A cat sits on the mat.")]
    )

    assert scores[0] == pytest.approx(1.0, abs=1e-4)


def test_an_unknown_method_is_refused():
    with pytest.raises(ValueError, match="Unknown method"):
        assistant.build_backend("nonsense")


# === Behaviour when the optional extra is not installed ===

WITHOUT_SBERT = pytest.mark.skipif(
    importlib.util.find_spec("sentence_transformers") is not None,
    reason="the assistant extra is installed",
)
WITHOUT_LEVENSHTEIN = pytest.mark.skipif(
    importlib.util.find_spec("Levenshtein") is not None,
    reason="the assistant extra is installed",
)


@WITHOUT_SBERT
def test_sbert_scoring_without_the_extra_says_how_to_install_it():
    backend = assistant.build_backend("sbert")

    with pytest.raises(click.ClickException, match=r"voc4cat\[assistant\]"):
        backend.label_scores(["a", "b"])


@WITHOUT_LEVENSHTEIN
def test_levenshtein_scoring_without_the_extra_says_how_to_install_it():
    backend = assistant.build_backend("levenshtein")

    with pytest.raises(click.ClickException, match=r"voc4cat\[assistant\]"):
        backend.label_scores(["a", "b"])
