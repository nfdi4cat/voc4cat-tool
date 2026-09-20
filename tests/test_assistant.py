"""Tests for the voc-assistant command line interface.

The command line layer and the Levenshtein backend are part of the default
install, so these tests run in CI. They drive the CLI with a simple scoring
backend instead of sentence-transformers; the sbert backend is covered by the
tests that are skipped when the `sbert` extra is absent.
"""

import importlib.util
import logging
import shutil
import subprocess
import sys
import textwrap

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


@pytest.fixture(autouse=True)
def outside_ci(monkeypatch):
    """Clear GITHUB_ACTIONS so the suite takes the non-CI path on gh-actions."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


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
    reason="the sbert extra is installed",
)


def test_the_levenshtein_backend_needs_no_extra():
    """It is a core dependency, so this works on a default install."""
    scores = assistant.build_backend("levenshtein").label_scores(
        ["co-precipitation", "coprecipitation"]
    )

    assert scores[0][1] > 0.9


@WITHOUT_SBERT
def test_sbert_scoring_without_the_extra_says_how_to_install_it():
    backend = assistant.build_backend("sbert")

    with pytest.raises(click.ClickException, match=r"voc4cat\[sbert\]"):
        backend.label_scores(["a", "b"])


@WITHOUT_SBERT
def test_sbert_scoring_without_the_extra_names_the_way_around_it():
    """The error is also the answer: it spells out the torch-free run."""
    backend = assistant.build_backend("sbert")

    with pytest.raises(click.ClickException) as excinfo:
        backend.label_scores(["a", "b"])

    message = str(excinfo.value)
    assert "--method levenshtein" in message
    assert "--definitions none" in message


# === Definition scoring can be turned off (the torch-free path) ===


class LabelOnlyBackend(ExactLabelBackend):
    """Refuses to score definitions, the way a run without sbert would."""

    def definition_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        msg = "definitions must not be scored in this run"
        raise AssertionError(msg)


class RecordingBackend(ExactLabelBackend):
    """Scores a chosen label pair below the certain threshold and records asks."""

    def __init__(self, undecided: float = 0.93) -> None:
        super().__init__()
        self.undecided = undecided
        self.asked: list[tuple[str, str]] = []

    def label_scores(self, sentences: list[str]) -> list[list[float]]:
        scores = super().label_scores(sentences)
        for i, first in enumerate(sentences):
            for j, second in enumerate(sentences):
                if i != j and first.casefold() != second.casefold():
                    scores[i][j] = self.undecided
        return scores

    def definition_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.asked.extend(pairs)
        return [0.9] * len(pairs)


def test_an_exact_duplicate_is_found_without_scoring_definitions(vocab, tmp_path, run):
    """Basic duplicate detection needs no semantic model at all."""
    output = tmp_path / "report.md"

    result = run(
        [
            "check",
            str(vocab),
            "--method",
            "levenshtein",
            "--definitions",
            "none",
            "--output",
            str(output),
        ],
        backend=LabelOnlyBackend(),
    )

    report = report_of(result, output)
    assert "0000001" in report
    assert "0000002" in report
    assert "not scored" in report


def test_turning_definitions_off_says_so_in_the_report(vocab, tmp_path, run):
    output = tmp_path / "report.md"

    result = run(
        ["check", str(vocab), "--definitions", "none", "--output", str(output)],
        backend=LabelOnlyBackend(),
    )

    assert "Definitions scored? No" in report_of(result, output)


def test_a_pair_that_only_the_definitions_could_decide_is_not_reported(
    vocab, tmp_path, run
):
    """Without a definition score there is nothing to justify reporting it."""
    output = tmp_path / "report.md"

    result = run(
        ["check", str(vocab), "--definitions", "none", "--output", str(output)],
        backend=RecordingBackend(),
    )

    findings = report_of(result, output).split("## Additional concept check")[0]

    rows = [line for line in findings.splitlines() if line.startswith("| [")]
    # Only the three exact "co-precipitation" matches survive. Every other
    # candidate scored 0.93, which the label alone cannot settle.
    assert len(rows) == 3
    assert all("| 1.0000 | not scored |" in row for row in rows)


def test_every_candidate_pair_is_scored_when_definitions_are_on(vocab, tmp_path, run):
    """The score fills a column even where the label alone settles the pair."""
    backend = RecordingBackend()

    result = run(
        ["check", str(vocab), "--output", str(tmp_path / "report.md")],
        backend=backend,
    )

    assert result.exit_code == 0, result.output
    co_precipitation = (
        "Precipitation of more than one substance at the same time "
        "from a common solution."
    )
    carried_down = (
        "The carrying down by a precipitate of substances normally soluble "
        "under the conditions used."
    )
    assert {co_precipitation, carried_down} in [set(pair) for pair in backend.asked]


def test_the_torch_free_path_imports_no_sentence_transformers(vocab, tmp_path):
    """Duplicate detection without sbert must not load sbert or torch.

    Checked in a subprocess because the tests above import both.
    """
    script = textwrap.dedent(f"""
        import sys
        from click.testing import CliRunner
        from voc4cat import assistant

        result = CliRunner().invoke(assistant.cli, [
            "check", r"{vocab}",
            "--method", "levenshtein",
            "--definitions", "none",
            "--config", r"{tmp_path / "absent.toml"}",
            "--output", r"{tmp_path / "torch_free.md"}",
        ], catch_exceptions=False)
        assert result.exit_code == 0, result.output
        assert "sentence_transformers" not in sys.modules, "sbert was imported"
        assert "torch" not in sys.modules, "torch was imported"
    """)

    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    report = (tmp_path / "torch_free.md").read_text(encoding="utf-8")
    assert "co-precipitation" in report
    assert "Definitions scored? No" in report


# === Logging ===


NOISY_LOGGERS = ("httpx", "huggingface_hub", "sentence_transformers", "transformers")


@pytest.fixture
def restore_logging(monkeypatch):
    """Undo what setup_logging does to the process-wide logging state."""
    monkeypatch.delenv("LOGLEVEL", raising=False)
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    levels = {name: logging.getLogger(name).level for name in NOISY_LOGGERS}
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    for name, previous in levels.items():
        logging.getLogger(name).setLevel(previous)


def test_importing_the_assistant_does_not_configure_logging():
    """A module import must not reconfigure logging for the whole process."""
    script = textwrap.dedent("""
        import logging
        assert not logging.getLogger().handlers, "root had handlers already"
        import voc4cat.assistant
        assert not logging.getLogger().handlers, "the import configured logging"
    """)

    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr


def test_the_loggers_of_the_scoring_libraries_are_silenced(
    vocab, tmp_path, run, restore_logging
):
    """An sbert run logs 33 httpx request lines at INFO; they are not news."""
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.NOTSET)

    result = run(["check", str(vocab), "--output", str(tmp_path / "r.md")])

    assert result.exit_code == 0, result.output
    assert [logging.getLogger(name).level for name in NOISY_LOGGERS] == [
        logging.WARNING
    ] * len(NOISY_LOGGERS)


def run_cli_in_subprocess(vocab, tmp_path, args):
    completed = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "voc4cat.assistant",
            "check",
            str(vocab),
            "--method",
            "levenshtein",
            "--definitions",
            "none",
            "--config",
            str(tmp_path / "absent.toml"),
            "--output",
            str(tmp_path / "report.md"),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stderr


def test_the_assistant_reports_progress_at_the_default_level(vocab, tmp_path):

    assert "INFO" in run_cli_in_subprocess(vocab, tmp_path, [])


def test_quiet_silences_the_progress_messages(vocab, tmp_path):

    assert "INFO" not in run_cli_in_subprocess(vocab, tmp_path, ["--quiet"])


def test_the_assistant_logs_to_a_file_when_asked(vocab, tmp_path):
    """Run out of process: under pytest basicConfig cannot set the root level."""
    logfile = tmp_path / "logs" / "assistant.log"

    run_cli_in_subprocess(vocab, tmp_path, ["--logfile", str(logfile)])

    assert "Submitted concepts" in logfile.read_text(encoding="utf-8")


def test_verbose_and_quiet_together_are_refused(vocab, tmp_path, run):
    """They contradict each other; voc4cat refuses the combination too."""
    result = run(["check", str(vocab), "-v", "-q", "--output", str(tmp_path / "r.md")])

    assert result.exit_code != 0
    assert "--verbose" in result.output


def test_the_definition_threshold_defaults_to_one_half(vocab, tmp_path, run):
    """A definition score is weak evidence, so it filters little by default.

    Measured over the 600 concepts of voc4cat: at 0.8 the threshold rejected
    every pair in the 0.90-0.98 label band, the best of them scoring 0.7907.
    """
    output = tmp_path / "report.md"

    result = run(["check", str(vocab), "--output", str(output)])

    assert "Similarity threshold definitions: 0.5" in report_of(result, output)


# === Exit code, for use in a CI pipeline ===


@pytest.fixture
def in_ci(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


def test_findings_are_advisory_outside_ci(vocab, tmp_path, run, caplog):
    """Locally the report is the output; the run itself still succeeds."""
    with caplog.at_level(logging.WARNING):
        result = run(["check", str(vocab), "--output", str(tmp_path / "r.md")])

    assert result.exit_code == 0, result.output
    assert "similarities" in caplog.text


def test_findings_fail_the_run_in_ci(vocab, tmp_path, run, in_ci):
    """With the known pairs accepted in the config, a finding is a problem."""
    result = run(["check", str(vocab), "--output", str(tmp_path / "r.md")])

    assert result.exit_code == 1
    assert "3" in result.output


def test_a_vocabulary_without_similarities_passes_in_ci(
    published, tmp_path, run, in_ci
):
    """The parent checks report W001 and W002 here, which are not duplicates."""
    output = tmp_path / "r.md"

    result = run(["check", str(published), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert "No additional concept issues found." not in output.read_text(
        encoding="utf-8"
    )


def test_accepted_findings_do_not_fail_the_run_in_ci(
    vocab, tmp_path, run, idranges, in_ci
):
    """Suppressing a known pair is what lets the pipeline go green."""
    accepted = "".join(
        "[[vocabs.myvocab.accepted_similarity]]\n"
        f'concepts = ["ex:{a}", "ex:{b}"]\n'
        'reason = "Reviewed."\n'
        for a, b in (
            ("0000001", "0000002"),
            ("0000001", "0000004"),
            ("0000002", "0000004"),
        )
    )

    result = run(
        [
            "check",
            str(vocab),
            "--config",
            idranges(accepted),
            "--output",
            str(tmp_path / "r.md"),
        ]
    )

    assert result.exit_code == 0, result.output


def test_the_report_is_written_even_when_the_run_fails(vocab, tmp_path, run, in_ci):
    """The pipeline needs the report to say what went wrong."""
    output = tmp_path / "r.md"

    result = run(["check", str(vocab), "--output", str(output)])

    assert result.exit_code == 1
    assert "co-precipitation" in output.read_text(encoding="utf-8")
