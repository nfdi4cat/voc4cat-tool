"""Module with checks that are related to the workflow.

These checks cannot be handled with pydantic model validation.
"""

import glob
import logging
import os
from itertools import chain
from pathlib import Path

from curies import Converter
from rdflib import RDF, SKOS, Graph, compare

from voc4cat import config

logger = logging.getLogger(__name__)


class Voc4catError(Exception):
    pass


def validate_config_has_idrange(vocab_name):
    """Check that the vocabulary has at least one id_range."""
    logger.debug('-> Validating ID range config for vocabulary "%s".', vocab_name)
    if config.IDRANGES.default_config:
        # no detailed config -> no check possible
        return
    if not getattr(config.IDRANGES.vocabs.get(vocab_name, {}), "id_range", []):
        msg = (
            "Config requires at least one ID range in a section [[vocabs.%s.id_range]]."
        )
        raise Voc4catError(msg % vocab_name)


def check_number_of_files_in_inbox(inbox_dir: Path, idranges: dict | None = None):
    """Check that inbox has not more than one file if single_vocab option is true."""
    idranges = config.IDRANGES if idranges is None else idranges
    inbox_files = glob.glob(str(inbox_dir / "*.xlsx"))
    logger.debug('-> Found %i xlsx files in "%s"', len(inbox_files), inbox_dir)
    if idranges.single_vocab and len(inbox_files) > 1:
        msg = 'The single vocabulary option is active but "%s" contains %s xlsx files.'
        raise Voc4catError(msg % (inbox_dir, len(inbox_files)))


def validate_vocabulary_files_for_ci_workflow(vocab_dir: Path, inbox_dir: Path):
    """Check if name of vocabulary is OK"""

    # (1) If config: Verify that xlsx-filenames (stem) present in inbox are defined in config
    # (2) If single vocab:
    # (3) If config: Verify that ttl-filenames (stem) present in /vocabularies are defined
    #     in config
    # All three checks are useful for voc4cat-template but not for voc4at-tool.

    if config.IDRANGES.default_config or not config.IDRANGES.vocabs:
        logger.warning(
            "To validate file names the config requires at least one vocabulary section."
        )
        return

    inbox_files = glob.glob(str(inbox_dir / "*.xlsx"))
    inbox_md_files = glob.glob(str(inbox_dir / "*.md"))
    inbox_all_files = glob.glob(str(inbox_dir / "*"))

    # Test that inbox has only xlsx files and md or txt doc files
    if len(inbox_all_files) > len(inbox_files) + len(inbox_md_files):
        if os.getenv("CI_RUN"):
            msg = f'Directory "{inbox_dir}" may only contain xlsx files and README.md.'
            raise Voc4catError(msg)
        logger.warning(
            'Directory "%s" should only contain xlsx files and README.md.',
            inbox_dir,
        )

    # By creating a set first duplicates are eliminated.
    vocab_files = glob.glob(str(vocab_dir / "*.ttl"))
    vocab_names = list({Path(fp).stem.lower() for fp in vocab_files})
    inbox_names = list({Path(fp).stem.lower() for fp in inbox_files})
    logger.debug("-> vocab name stems: %s", ", ".join(vocab_names))
    logger.debug("-> inbox name stems: %s", ", ".join(inbox_names))

    vocab_names_in_config = [name.lower() for name in config.IDRANGES.vocabs]
    logger.debug("-> config vocab names: %s", ", ".join(vocab_names_in_config))

    if config.IDRANGES.single_vocab:
        if len(vocab_names) > 1:
            msg = 'Directory "%s" may contain only a single vocabulary.'
            raise Voc4catError(msg % vocab_dir)

        if (
            len(vocab_names) == 1
            and len(inbox_names) == 1
            and vocab_names[0] != inbox_names[0]
        ):
            msg = 'The file in inbox "%s" must match the vocabulary name "%s".'
            raise Voc4catError(msg % (inbox_files[0], vocab_names[0]))

        if len(vocab_names) == 1 and vocab_names[0] not in vocab_names_in_config:
            msg = 'Vocabulary "%s" in "%s" must be also present in config.'
            raise Voc4catError(msg % (vocab_names[0], vocab_dir))

        if len(inbox_names) == 1 and inbox_names[0] not in vocab_names_in_config:
            msg = 'New vocabulary "%s" in "%s" must be also present in config.'
            raise Voc4catError(msg % (inbox_names[0], inbox_dir))

    # If more than one vocabulary is allowed, we can only check that all
    # file name stems are present in config.IDRANGES.
    missing_in_config = [
        name
        for name in chain(vocab_names, inbox_names)
        if name not in vocab_names_in_config
    ]
    if missing_in_config:
        msg = 'Missing vocabulary id_range config for "%s".'
        raise Voc4catError(msg % ", ".join(missing_in_config))


def check_for_removed_iris(prev_vocab: Path, new_vocab: Path):
    """
    Validate that concepts/collection were not removed from prev_vocab to new_vocab.

    Logs a warning for removed parts and raises a Voc4catError exception if
    the configuration [vocabs.prev_vocab.checks] sets allow_delete to True.
    """
    logger.debug(
        "-> Checking changes between %s (previous) and %s (new)", prev_vocab, new_vocab
    )

    prev = Graph()
    prev.parse(prev_vocab.resolve().as_uri(), format="turtle")
    new = Graph()
    new.parse(new_vocab.resolve().as_uri(), format="turtle")

    _, in_prev, _ = compare.graph_diff(prev, new)
    # print("Only in 1st\n", in_prev.serialize(format="turtle"))
    # print("Only in 2nd\n", in_new.serialize(format="turtle"))

    voc = config.IDRANGES.vocabs.get(prev_vocab.stem, {})
    delete_allowed = voc.checks.allow_delete if getattr(voc, "checks", False) else False
    if in_prev:
        removed = 0
        for iri in in_prev.subjects(RDF.type, SKOS.Concept):
            msg = "-> Removal of a Concept detected: %s"
            if delete_allowed:
                logger.warning(msg, iri)
            else:
                logger.error(msg, iri)
            removed += 1
        for iri in in_prev.subjects(RDF.type, SKOS.Collection):
            msg = "-> Removal of a Collection detected: %s"
            if delete_allowed:
                logger.warning(msg, iri)
            else:
                logger.error(msg, iri)
            removed += 1
        if not delete_allowed and removed:
            msg = f"Forbidden removal of {removed} concepts/collections detected. See log for IRIs."
            raise Voc4catError(msg)
    else:
        logger.debug("-> No removals detected.")


def check_hierarchical_redundancy(vocab_path: Path) -> list[tuple[str, str, str]]:
    """
    Detect redundant hierarchical relationships in a SKOS vocabulary.

    A redundant relationship exists when concept C has skos:broader to both
    B and A, where A is already an ancestor of B (reachable via skos:broader).

    Returns list of tuples (concept_curie, redundant_ancestor_curie, intermediate_parent_curie)
    for each redundant relationship found. The triple to eliminate is:
    <concept> skos:broader <redundant_ancestor>
    """
    logger.debug("-> Checking for hierarchical redundancy in %s", vocab_path)

    g = Graph()
    g.parse(vocab_path.resolve().as_uri(), format="turtle")

    # Build curies converter from graph's namespace bindings
    converter = Converter.from_prefix_map(
        {prefix: str(uri) for prefix, uri in g.namespaces()}
    )

    redundancies = []
    for concept, parent1 in sorted(g.subject_objects(SKOS.broader)):
        for parent2 in sorted(g.objects(concept, SKOS.broader)):
            if parent1 == parent2:
                continue  # must be different parents
            # Check if parent2 is an ancestor of parent1 (reachable via broader)
            if parent2 in g.transitive_objects(parent1, SKOS.broader):
                redundancies.append(
                    (
                        converter.compress(str(concept), passthrough=True),
                        converter.compress(str(parent2), passthrough=True),
                        converter.compress(str(parent1), passthrough=True),
                    )
                )

    return redundancies
