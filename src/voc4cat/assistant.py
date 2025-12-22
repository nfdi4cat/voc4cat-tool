"""
Vocabulary Assistant CLI tool.

This tool helps vocabulary maintainers to check for similarities between concepts in vocabularies.
It uses Sentence Transformers for semantic similarity and Levenshtein ratio for string similarity.

It also provides a command-line interface (CLI) for easy usage.

Author: David Linke (gh:dalito), 2025
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click
from Levenshtein import ratio
from rdflib import RDF, SKOS, Graph
from sentence_transformers import SentenceTransformer
from torch import Tensor

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Local base URL for voc4cat
base_url = "http://127.0.0.1:5500/voc4cat-outbox_2025-04-16T0925_run14489333337/voc4cat/index.html#"
# In-development base URL for voc4cat
base_url = "https://nfdi4cat.github.io/voc4cat/dev/voc4cat/index.html#"


class Problem(Enum):
    """Enumeration for concept issues."""

    NO_BROADER_CONCEPT = ("W001", "No broader concept")
    MULTIPLE_BROADER_CONCEPTS = ("W002", "Multiple broader concepts")

    def __init__(self, problem_id, description):
        self.problem_id = problem_id
        self.description = description


@dataclass
class Concept:
    """Class to hold concept information."""

    uri: str
    curie: str
    pref_label: str
    alt_labels: str
    definition: str
    parents: str


@dataclass
class ConceptSimilarity:
    """Class to hold concept similarity information."""

    concept_id: str
    sentence_key: str
    similar_concept_id: str
    similar_sentence_key: str
    similarity_score: float
    definition_similarity_score: float
    have_same_broader_concept: bool


@dataclass
class ConceptIssue:
    """Class to hold concept issue information."""

    concept_id: str
    concept_label: str
    problem: Problem
    problem_detail: str


def load_vocab(ttl_file: Path) -> dict:
    """Return list of Concept instances."""
    vocab_graph = Graph().parse(str(ttl_file), format="turtle")
    concepts = {}
    for s in vocab_graph.subjects(RDF.type, SKOS.Concept):
        holder = {}
        concept_id = str(s)
        holder["uri"] = str(s)
        holder["curie"] = (
            str(s).split("/")[-1].replace("_", ":")
        )  # TODO use a function to convert URI to CURIE
        holder["alt_labels"] = []
        holder["parents"] = []
        for p, o in vocab_graph.predicate_objects(s):
            if p == SKOS.pref_label:
                holder["pref_label"] = str(o)  # .toPython()
            if p == SKOS.altLabel:
                holder["alt_labels"].append(str(o))
            if p == SKOS.definition:
                holder["definition"] = str(o)
            if p == SKOS.broader:
                holder["parents"].append(str(o))
        concepts[concept_id] = Concept(**holder)
    return concepts


class CompareVocabularies:
    """Compare vocabularies using Sentence Transformers and Levenshtein ratio."""

    def __init__(self, vocab_new: Path, vocab_base: Path | None = None) -> None:
        """Initialize the CompareVocabularies class."""
        self.vocab_new_src = vocab_new
        self.vocab_new = load_vocab(vocab_new)
        self.vocab_base_src = vocab_base
        if vocab_base is None:
            self.vocab_base = {}
        else:
            self.vocab_base = load_vocab(vocab_base)
        self.added_concepts = {
            k: v for k, v in self.vocab_new.items() if k not in self.vocab_base
        }
        self.idx_new = [
            i for i, uri in enumerate(self.vocab_new) if uri in self.added_concepts
        ]
        self.model = None

        logger.info("Known concepts    : %d", len(self.vocab_base))
        logger.info("Submitted concepts: %d", len(self.vocab_new))
        logger.info("New concepts added: %d", len(self.added_concepts))
        logger.debug("idx of new concepts: %s", self.idx_new)

    def get_similarities_sbert(self, sentences, model="all-MiniLM-L6-v2") -> Tensor:
        """
        Determine similarity using Sentence Transformers.

        Documentation: https://sbert.net/
        Publication: https://arxiv.org/abs/1908.10084
        """
        logger.debug("Entering get_similarities_sbert method.")
        if self.model is None:
            # Load the model
            self.model = SentenceTransformer(model)
            logger.debug("model %s loaded.", model)
        # Compute embeddings
        embeddings = self.model.encode(sentences)
        logger.debug("Embeddings calculated.")
        # Compute cosine similarities
        similarities = self.model.similarity(embeddings, embeddings)
        logger.debug("sbert similarities calculated.")
        return similarities

    def get_similarities_levenshtein(self, sentences) -> list:
        """
        Determine Levenshtein similarity after normalising terms.

        Normalisation includes stripping whitespace, converting to lowercase,
        and replacing hyphens with spaces.
        """
        logger.debug("Entering get_similarities_levenshtein method.")
        sentences = [s.strip().lower().replace("-", " ") for s in sentences]
        similarities: list = []
        for i, sentence1 in enumerate(sentences):
            similarities.append([])
            for j, sentence2 in enumerate(sentences):
                if i >= j:
                    similarities[i].append(-1)
                else:
                    similarities[i].append(ratio(sentence1, sentence2))
        logger.debug("Levenshtein similarities calculated.")
        return similarities

    def find_similarities(
        self, labeled_sentences, similarities, thresholds, compare_all
    ):
        """
        Find and print similarities between new concepts and existing concepts.
        """
        threshold_labels, threshold_definitions = thresholds
        sentences = list(labeled_sentences.values())
        keys = list(labeled_sentences.keys())
        reportable_similarities = []
        for idx_i, sentence1 in enumerate(sentences):
            # Only list similarities for new concepts
            if (not compare_all) or (idx_i not in self.idx_new):
                continue
            for idx_j, sentence2 in enumerate(sentences):
                if idx_i == idx_j:
                    continue
                # Skip listing similarity between two new concepts twice (A-B and B-A)
                if idx_j in self.idx_new and idx_i >= idx_j:
                    continue
                if similarities[idx_i][idx_j] > threshold_labels:
                    id_i = keys[idx_i][0]
                    id_j = keys[idx_j][0]
                    if id_i == id_j:  # same concept
                        continue
                    # Check how similar the definitions are (using Sentence Transformers)
                    pair_definition_similarity = float(
                        self.get_similarities_sbert(
                            [
                                self.vocab_new[id_i].definition,
                                self.vocab_new[id_j].definition,
                            ]
                        )[0][1]
                    )
                    if pair_definition_similarity < threshold_definitions:
                        continue
                    # Check if the concepts have the same broader concept (set intersection)
                    have_same_broader_concept = bool(
                        set(self.vocab_new[id_i].parents)
                        & set(self.vocab_new[id_j].parents)
                    )
                    logger.debug(
                        "%s (%s) - %s (%s): %.4f",
                        sentence1,
                        id_i,
                        sentence2,
                        id_j,
                        similarities[idx_i][idx_j],
                    )
                    reportable_similarities.append(
                        ConceptSimilarity(
                            concept_id=id_i,
                            sentence_key=keys[idx_i],
                            similar_concept_id=id_j,
                            similar_sentence_key=keys[idx_j],
                            similarity_score=float(similarities[idx_i][idx_j]),
                            definition_similarity_score=pair_definition_similarity,
                            have_same_broader_concept=have_same_broader_concept,
                        )
                    )
        return reportable_similarities

    def compare_concept_labels(
        self,
        method,
        include_alt_labels,
        threshold_labels,
        threshold_definitions,
        compare_all,  # true=compare all concepts, false=just new ones
    ) -> dict:
        new_vocab_labels = {
            (k, "pref_label"): v.pref_label.strip() for k, v in self.vocab_new.items()
        }
        if include_alt_labels:
            # Include alt_labels in the comparison
            new_vocab_alt_labels = {}
            for k, v in self.vocab_new.items():
                for i, alt_label in enumerate(v.alt_labels):
                    new_vocab_alt_labels[(k, f"altLabel-{i}")] = alt_label
            new_vocab_labels.update(new_vocab_alt_labels)
        sentences = list(new_vocab_labels.values())
        if method == "sbert":
            # Use Sentence Transformers for semantic similarity
            similarities = self.get_similarities_sbert(sentences)
        elif method == "levenshtein":
            # Use Levenshtein ratio for string similarity
            similarities = self.get_similarities_levenshtein(sentences)
        else:
            msg = f"Unknown method: {method}"
            raise ValueError(msg)
        return {
            "method": method,
            "uses_alt_labels": "Yes" if include_alt_labels else "No",
            "threshold_labels": threshold_labels,
            "threshold_definitions": threshold_definitions,
            "compare_all": compare_all,
            "data": self.find_similarities(
                new_vocab_labels,
                similarities,
                thresholds=(threshold_labels, threshold_definitions),
                compare_all=compare_all,
            ),
        }

    def check_parents(self, method="sbert") -> dict:
        """Check if the concepts have no or more than one broader concept."""
        logger.info("Checking if concepts have no or more than one broader concept.")
        concept_problems = {}
        for id_, concept in self.vocab_new.items():
            if not concept.parents:
                concept_problems[id_] = ConceptIssue(
                    concept_id=concept.curie,
                    concept_label=concept.pref_label,
                    problem=Problem.NO_BROADER_CONCEPT,
                    problem_detail="",
                )
            elif len(concept.parents) > 1:
                details = " / ".join(
                    [
                        f"[{self.vocab_new[id_].pref_label}]({base_url + id_})"
                        for id_ in concept.parents
                    ]
                )
                concept_problems[id_] = ConceptIssue(
                    concept_id=concept.curie,
                    concept_label=concept.pref_label,
                    problem=Problem.MULTIPLE_BROADER_CONCEPTS,
                    problem_detail=details,
                )
        return concept_problems

    def markdown_report(self, results: dict) -> None:
        """Generate a markdown report of the similarities found."""
        method = results["method"]
        report = []
        if results["compare_all"]:
            report.append(
                f"# Similarities for all concepts using method {method}\n\n"
                f"Checked {len(self.vocab_new)} concepts in {self.vocab_new_src} for similarities.\n\n"
            )
        else:
            report.append(
                f"# Similarities for added concepts using method {method}\n\n"
                f"Checked {len(self.added_concepts)} additions made in {self.vocab_new_src} "
                f"for similarities with concepts in {self.vocab_base_src}.\n\n"
            )

        report.append(f"- Similarity threshold labels: {results['threshold_labels']}\n")
        report.append(
            f"- Similarity threshold definitions: {results['threshold_definitions']}\n"
        )
        report.append(
            f"- Alternate labels included in check? {results['uses_alt_labels']}\n\n"
        )
        if not results["data"]:
            report.append("No similarities found.\n")
        else:
            report.append(
                f"| {'Concept ID':<15} | {'Concept label':<27} | {'Similar<BR>Concept ID':<15} "
                f"| {'Similar Concept label':<25} | {'Similarity Score<BR>Label':<20} "
                f"| {'Similarity Score<BR>Definition':<30} | {'Same Broader Concept?'} |\n"
            )
            report.append(
                f"|{'-' * 17}|{'-' * 32}|{'-' * 17}|{'-' * 32}|{'-' * 15}|{'-' * 15}|{'-' * 15}|\n"
            )
        similar_concept_pairs = []
        for rec in results["data"]:
            # avoid repeated reporting of pairs that have pref_label and altLabel similarity
            pair = {rec.concept_id, rec.similar_concept_id}
            if pair in similar_concept_pairs:
                continue
            similar_concept_pairs.append(pair)

            concept = self.vocab_new[rec.concept_id]
            concept_label = (
                concept.pref_label
                if rec.sentence_key[1] == "pref_label"
                else concept.alt_labels[int(rec.sentence_key[1].split("-")[-1])]
            )
            similar_concept = self.vocab_new[rec.similar_concept_id]
            similar_concept_label = (
                similar_concept.pref_label
                if rec.similar_sentence_key[1] == "pref_label"
                else similar_concept.alt_labels[
                    int(rec.similar_sentence_key[1].split("-")[-1])
                ]
                + "(altLabel)"
            )
            concept_parents = self.vocab_new[rec.concept_id].parents
            if rec.have_same_broader_concept:
                broader_concepts = ", ".join(
                    [
                        f"[{self.vocab_new[id_].pref_label}]({base_url + id_})"
                        for id_ in concept_parents
                    ]
                )
            else:
                similar_concept_parents = self.vocab_new[rec.similar_concept_id].parents
                broader_concepts = (
                    ", ".join(
                        [
                            f"[{self.vocab_new[id_].pref_label}]({base_url + id_})"
                            for id_ in concept_parents
                        ]
                    )
                    + " / "
                    + ", ".join(
                        [
                            f"[{self.vocab_new[id_].pref_label}]({base_url + id_})"
                            for id_ in similar_concept_parents
                        ]
                    )
                )
            report.append(
                f"| [{concept.curie}]({base_url + concept.uri}) | {concept_label:<30} "
                f"| [{similar_concept.curie}]({base_url + similar_concept.uri}) | {similar_concept_label:<30} "
                f"| {rec.similarity_score:.4f} | {rec.definition_similarity_score:.4f} "
                f"| {'Y' if rec.have_same_broader_concept else 'N'} - {broader_concepts} |\n"
            )

        parent_check_report = self.check_parents(method=method)
        report.append("\n\n## Additional concept check results\n\n")
        if parent_check_report:
            report.append(
                f"| {'Concept ID':<15} | {'Concept label':<27} | {'Problem ID':<15} "
                f"| {'Problem description':<25} | {'Problem details':<20} |\n"
            )
            report.append(f"|{'-' * 17}|{'-' * 32}|{'-' * 17}|{'-' * 32}|{'-' * 22}|\n")
            for id_, rec in sorted(parent_check_report.items()):
                report.append(
                    f"| [{rec.concept_id}]({base_url + id_}) | {rec.concept_label:<30} "
                    f"| {rec.problem.problem_id} | {rec.problem.description:<30} | {rec.problem_detail} |\n"
                )
        else:
            report.append("\n## No additional concept issues found.\n")

        fname = (
            f"check_report_{method}.md"
            if results["compare_all"]
            else f"compare_report_{method}.md"
        )
        with open(fname, "w") as f:
            f.writelines(report)
        logger.info("Similarities report written to %s", fname)


@click.group()
def cli():
    """CLI tool for vocabulary maintainers."""


@cli.command("check")
@click.argument("vocab_src", type=Path)
@click.option(
    "--method",
    type=click.Choice(["sbert", "levenshtein"]),
    default="sbert",
    help="Method to use for similarity comparison",
)
@click.option(
    "--include-alt-labels",
    is_flag=True,
    help="Include alt_labels in the comparison",
    default=True,
)
@click.option(
    "--threshold-labels", type=float, help="Threshold for label similarity", default=0.9
)
@click.option(
    "--threshold-defs",
    type=float,
    help="Threshold for definition similarity",
    default=0.8,
)
def find_similarities_in_one_vocab(
    vocab_src: Path,
    method: str,
    include_alt_labels: bool,
    threshold_labels: float,
    threshold_defs: float,
) -> None:
    """Find similarities between concepts in a single vocabulary."""
    logger.info("Finding similarities in vocabulary: %s", vocab_src)
    # Add logic for finding similarities here
    vocab = CompareVocabularies(vocab_src)
    results = vocab.compare_concept_labels(
        method,
        include_alt_labels,
        threshold_labels=threshold_labels,
        threshold_definitions=threshold_defs,
        compare_all=True,
    )
    vocab.markdown_report(results)


@cli.command("compare")
@click.argument("vocab_src", type=Path)
@click.argument("vocab_new_src", type=Path)
@click.option(
    "--method",
    type=click.Choice(["sbert", "levenshtein"]),
    default="sbert",
    help="Method to use for similarity comparison",
)
@click.option(
    "--include-alt-labels",
    is_flag=True,
    help="Include alt_labels in the comparison",
    default=True,
)
@click.option(
    "--threshold-labels", type=float, help="Threshold for label similarity", default=0.9
)
@click.option(
    "--threshold-defs",
    type=float,
    help="Threshold for definition similarity",
    default=0.8,
)
def compare_vocabularies(
    vocab_src: Path,
    vocab_new_src: Path,
    method: str,
    include_alt_labels: bool,
    threshold_labels: float,
    threshold_defs: float,
) -> None:
    """Compare two vocabularies and check additions for similarity with existing concepts."""
    logger.info(
        "Checking additions made in %s for similarities with concepts in %s",
        vocab_new_src,
        vocab_src,
    )
    vocab_old_new = CompareVocabularies(vocab_new_src, vocab_src)
    results = vocab_old_new.compare_concept_labels(
        method,
        include_alt_labels,
        threshold_labels=threshold_labels,
        threshold_definitions=threshold_defs,
        compare_all=False,
    )
    vocab_old_new.markdown_report(results)


if __name__ == "__main__":
    cli()
