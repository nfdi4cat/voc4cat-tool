"""
Vocabulary Assistant CLI tool.

This tool helps vocabulary maintainers to check for similarities between
concepts in vocabularies. It uses Sentence Transformers for semantic
similarity and Levenshtein ratio for string similarity.

This module holds the command line interface and the scoring backends. The
logic that decides what is reported lives in :mod:`voc4cat.similarity`, which
needs none of the optional dependencies.

Author: David Linke (gh:dalito), 2025
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import click

from voc4cat import config, similarity

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"

MISSING_EXTRA = (
    "Scoring needs the optional dependencies of voc-assistant. "
    'Install them with: pip install "voc4cat[assistant]"'
)


class Backend(Protocol):
    """Scores labels against each other and definitions pair by pair."""

    def label_scores(self, sentences: list[str]) -> list[list[float]]:
        """Return a score matrix over `sentences`; only i<j is read."""
        ...

    def definition_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Return the similarity of each pair of definitions."""
        ...


@dataclass
class ScoringBackend:
    """Scores labels with the chosen method and definitions with sbert.

    Definitions are compared semantically whichever method scores the labels,
    because two independently worded definitions of the same thing share few
    characters.
    """

    method: str
    model_name: str = DEFAULT_MODEL
    _model: Any = field(default=None, init=False, repr=False)

    def label_scores(self, sentences: list[str]) -> list[list[float]]:
        if self.method == "sbert":
            return self._sbert_matrix(sentences)
        return self._levenshtein_matrix(sentences)

    def definition_scores(self, pairs: list[tuple[str, str]]) -> list[float]:
        """Score every pair from a single embedding pass over the texts."""
        if not pairs:
            return []
        model = self._sbert_model()
        texts = sorted({text for pair in pairs for text in pair})
        position = {text: index for index, text in enumerate(texts)}
        embeddings = model.encode(texts)
        similarities = model.similarity(embeddings, embeddings)
        return [
            float(similarities[position[first]][position[second]])
            for first, second in pairs
        ]

    def _sbert_model(self) -> Any:
        """
        Load the sentence-transformers model once.

        Documentation: https://sbert.net/
        Publication: https://arxiv.org/abs/1908.10084
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            except ImportError as err:
                raise click.ClickException(MISSING_EXTRA) from err
            self._model = SentenceTransformer(self.model_name)
            logger.debug("model %s loaded.", self.model_name)
        return self._model

    def _sbert_matrix(self, sentences: list[str]) -> list[list[float]]:
        model = self._sbert_model()
        embeddings = model.encode(sentences)
        logger.debug("Embeddings calculated.")
        matrix: list[list[float]] = model.similarity(embeddings, embeddings).tolist()
        logger.debug("sbert similarities calculated.")
        return matrix

    def _levenshtein_matrix(self, sentences: list[str]) -> list[list[float]]:
        """
        Determine Levenshtein similarity after normalising terms.

        Normalisation includes stripping whitespace, converting to lowercase,
        and replacing hyphens with spaces.
        """
        try:
            from Levenshtein import ratio  # noqa: PLC0415
        except ImportError as err:
            raise click.ClickException(MISSING_EXTRA) from err
        normalised = [s.strip().lower().replace("-", " ") for s in sentences]
        matrix: list[list[float]] = []
        for i, first in enumerate(normalised):
            # The half below the diagonal is never read; -1 keeps it out of
            # any comparison that does read it.
            matrix.append(
                [
                    -1.0 if i >= j else ratio(first, second)
                    for j, second in enumerate(normalised)
                ]
            )
        logger.debug("Levenshtein similarities calculated.")
        return matrix


def build_backend(method: str) -> Backend:
    """Return the scoring backend for a method name."""
    if method not in ("sbert", "levenshtein"):
        msg = f"Unknown method: {method}"
        raise ValueError(msg)
    return ScoringBackend(method=method)


@dataclass(frozen=True)
class AssistantSettings:
    """The options that both subcommands share."""

    method: str
    include_alt_labels: bool
    score_definitions: bool
    thresholds: similarity.Thresholds
    config_file: Path
    output: Path | None
    hide_accepted: bool


def run_comparison(
    vocab_new_src: Path,
    vocab_base_src: Path | None,
    settings: AssistantSettings,
    backend: Backend | None = None,
) -> Path:
    """Compare a vocabulary, write the report and return where it was written.

    With `vocab_base_src` the search is limited to the concepts that
    `vocab_new_src` adds; without it the whole vocabulary is screened.
    """
    scorer = backend if backend is not None else build_backend(settings.method)
    compare_all = vocab_base_src is None
    vocab_name = vocab_new_src.stem.lower()
    config.load_config(settings.config_file)
    vocab_config = config.IDRANGES.vocabs.get(vocab_name)
    converter = config.CURIES_CONVERTER_MAP.get(vocab_name)

    concepts = similarity.load_vocab(vocab_new_src, converter)
    published = (
        {}
        if vocab_base_src is None
        else similarity.load_vocab(vocab_base_src, converter)
    )
    added = {uri for uri in concepts if uri not in published}
    logger.info("Known concepts    : %d", len(published))
    logger.info("Submitted concepts: %d", len(concepts))
    logger.info("New concepts added: %d", len(added))

    labels = similarity.build_label_sentences(concepts, settings.include_alt_labels)
    candidates = similarity.select_candidates(
        labels,
        scorer.label_scores(list(labels.values())),
        settings.thresholds,
        None if compare_all else similarity.keys_of_concepts(labels, added),
    )
    findings = similarity.apply_definition_rule(
        candidates,
        _definition_scores(candidates, concepts, scorer)
        if settings.score_definitions
        else {},
        settings.thresholds,
        concepts,
    )
    accepted = similarity.resolve_accepted(
        vocab_config.accepted_similarity if vocab_config else [], converter
    )
    link_style = similarity.LinkStyle(
        template=vocab_config.concept_url_template if vocab_config else "",
        id_pattern=config.ID_PATTERNS.get(vocab_name),
    )
    result = similarity.ComparisonResult(
        method=settings.method,
        vocab_new_src=vocab_new_src,
        vocab_base_src=vocab_base_src,
        concepts=concepts,
        added_count=len(added),
        compare_all=compare_all,
        include_alt_labels=settings.include_alt_labels,
        definitions_scored=settings.score_definitions,
        thresholds=settings.thresholds,
        findings=similarity.partition_accepted(
            findings, accepted, concepts, report_unmatched=compare_all
        ),
        issues=similarity.check_parents(concepts, link_style),
    )
    destination = settings.output or Path(
        f"{'check' if compare_all else 'compare'}_report_{settings.method}.md"
    )
    similarity.write_report(
        similarity.render_report(result, link_style, settings.hide_accepted),
        destination,
    )
    return destination


def _definition_scores(
    candidates: list[similarity.CandidatePair],
    concepts: dict[str, similarity.Concept],
    scorer: Backend,
) -> dict[frozenset[str], float]:
    """Score the definitions of the candidate pairs in one pass."""
    pairs = [
        (
            concepts[pair.concept_id].definition,
            concepts[pair.similar_concept_id].definition,
        )
        for pair in candidates
    ]
    scores = scorer.definition_scores(pairs)
    return {
        similarity.pair_key(pair.concept_id, pair.similar_concept_id): score
        for pair, score in zip(candidates, scores, strict=True)
    }


def _settings(options: dict[str, Any]) -> AssistantSettings:
    """Turn the parsed command line options into settings."""
    try:
        thresholds = similarity.Thresholds(
            labels=options["threshold_labels"],
            definitions=options["threshold_defs"],
            labels_certain=options["threshold_labels_certain"],
        )
    except ValueError as err:
        raise click.BadParameter(str(err)) from err
    return AssistantSettings(
        method=options["method"],
        include_alt_labels=options["include_alt_labels"],
        score_definitions=options["definitions"] != "none",
        thresholds=thresholds,
        config_file=options["config_file"],
        output=options["output"],
        hide_accepted=options["hide_accepted"],
    )


def similarity_options(command: Callable[..., Any]) -> Callable[..., Any]:
    """Apply the options that `check` and `compare` have in common."""
    options = [
        click.option(
            "--method",
            type=click.Choice(["sbert", "levenshtein"]),
            default="sbert",
            help="Method to use for similarity comparison",
        ),
        click.option(
            "--include-alt-labels/--no-alt-labels",
            default=True,
            help="Include alternate labels in the comparison",
        ),
        click.option(
            "--definitions",
            type=click.Choice(["sbert", "none"]),
            default="sbert",
            show_default=True,
            help=(
                "How to score definitions. 'none' skips it, so only labels "
                "above --threshold-labels-certain are reported and no "
                "sentence-transformers model is needed."
            ),
        ),
        click.option(
            "--threshold-labels",
            type=float,
            default=0.9,
            help="Threshold for label similarity",
        ),
        click.option(
            "--threshold-defs",
            type=float,
            default=0.8,
            help="Threshold for definition similarity",
        ),
        click.option(
            "--threshold-labels-certain",
            type=float,
            default=0.98,
            help=(
                "Label similarity that is reported whatever the definitions "
                "score. Must not be below --threshold-labels."
            ),
        ),
        click.option(
            "--config",
            "config_file",
            type=click.Path(dir_okay=False, path_type=Path),
            default=Path("idranges.toml"),
            show_default=True,
            help="Configuration with accepted_similarity and concept_url_template",
        ),
        click.option(
            "-o",
            "--output",
            type=click.Path(dir_okay=False, writable=True, path_type=Path),
            default=None,
            help="Where to write the report [default: <command>_report_<method>.md]",
        ),
        click.option(
            "--hide-accepted",
            is_flag=True,
            default=False,
            help="Leave the accepted similarities out of the report",
        ),
    ]
    for option in reversed(options):
        command = option(command)
    return command


VOCAB_ARGUMENT = click.Path(exists=True, dir_okay=False, path_type=Path)


@click.group()
def cli() -> None:
    """CLI tool for vocabulary maintainers."""


@cli.command("check")
@click.argument("vocab_src", type=VOCAB_ARGUMENT)
@similarity_options
def find_similarities_in_one_vocab(vocab_src: Path, **options: Any) -> None:
    """Find similarities between concepts in a single vocabulary."""
    logger.info("Finding similarities in vocabulary: %s", vocab_src)
    run_comparison(vocab_src, None, _settings(options))


@cli.command("compare")
@click.argument("vocab_src", type=VOCAB_ARGUMENT)
@click.argument("vocab_new_src", type=VOCAB_ARGUMENT)
@similarity_options
def compare_vocabularies(vocab_src: Path, vocab_new_src: Path, **options: Any) -> None:
    """Compare two vocabularies and check additions against existing concepts."""
    logger.info(
        "Checking additions made in %s for similarities with concepts in %s",
        vocab_new_src,
        vocab_src,
    )
    run_comparison(vocab_new_src, vocab_src, _settings(options))


if __name__ == "__main__":
    cli()
