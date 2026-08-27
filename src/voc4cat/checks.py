"""Module with checks that are related to the workflow.

These checks cannot be handled with pydantic model validation.
"""

import glob
import logging
import os
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from typing import cast

from curies import Converter
from rdflib import RDF, SKOS, Graph, URIRef, compare

from voc4cat import config
from voc4cat.config import IDrangeConfig

logger = logging.getLogger(__name__)


class Voc4catError(Exception):
    pass


def validate_config_has_idrange(vocab_name: str) -> None:
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


def check_number_of_files_in_inbox(
    inbox_dir: Path, idranges: IDrangeConfig | None = None
) -> None:
    """Check that inbox has not more than one file if single_vocab option is true."""
    idranges = config.IDRANGES if idranges is None else idranges
    inbox_files = glob.glob(str(inbox_dir / "*.xlsx"))
    logger.debug('-> Found %i xlsx files in "%s"', len(inbox_files), inbox_dir)
    if idranges.single_vocab and len(inbox_files) > 1:
        msg = 'The single vocabulary option is active but "%s" contains %s xlsx files.'
        raise Voc4catError(msg % (inbox_dir, len(inbox_files)))


def validate_vocabulary_files_for_ci_workflow(vocab_dir: Path, inbox_dir: Path) -> None:
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


def check_for_removed_iris(prev_vocab: Path, new_vocab: Path) -> None:
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

    voc = config.IDRANGES.vocabs.get(prev_vocab.stem.lower())
    delete_allowed = voc.checks.allow_delete if voc is not None else False
    if in_prev:
        removed = 0
        for iri in in_prev.subjects(RDF.type, SKOS.Concept):
            msg = "-> Removal of a Concept detected: %s"
            if delete_allowed:
                logger.warning(msg, iri)
            else:
                logger.error(msg, iri)
            removed += 1
        collections = set(in_prev.subjects(RDF.type, SKOS.Collection)) | set(
            in_prev.subjects(RDF.type, SKOS.OrderedCollection)
        )
        for iri in collections:
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


def _typed_entity_iris(vocab: Path) -> set[str]:
    """Collect the IRIs of all concepts and collections in a vocabulary file."""
    graph = Graph()
    graph.parse(vocab.resolve().as_uri(), format="turtle")
    return {
        str(iri)
        for skos_type in (SKOS.Concept, SKOS.Collection, SKOS.OrderedCollection)
        for iri in graph.subjects(RDF.type, skos_type)
    }


def _iris_with_forbidden_ids(
    iris: set[str],
    vocab_name: str,
    granted: list[tuple[int, int]],
    actor: str,
) -> list[str]:
    """Select the IRIs whose ID is not covered by any of the granted ranges."""
    voc = config.IDRANGES.vocabs[vocab_name]
    permanent_iri_part = str(voc.permanent_iri_part)
    id_pattern = config.ID_PATTERNS[vocab_name]
    granted_text = ", ".join(f"{first}-{last}" for first, last in granted)

    forbidden = []
    for iri in sorted(iris):
        if not iri.startswith(permanent_iri_part):
            # IRIs of other vocabularies may be referenced; their IDs are not ours.
            continue
        match = id_pattern.search(iri)
        if match is None:
            logger.error(
                "-> New IRI %s has no ID matching the configured pattern of %i digits.",
                iri,
                voc.id_length,
            )
            forbidden.append(iri)
            continue
        id_ = int(match["identifier"])
        if not any(first <= id_ <= last for first, last in granted):
            logger.error(
                '-> New IRI %s is outside the ID range(s) of actor "%s": %s',
                iri,
                actor,
                granted_text,
            )
            forbidden.append(iri)
    return forbidden


def check_new_ids_in_actor_range(
    prev_vocab: Path | None, new_vocab: Path, actor: str
) -> None:
    """
    Validate that IRIs added in new_vocab use IDs granted to actor.

    IDs are granted per vocabulary and an actor may hold several disjoint
    ranges. IRIs already present in prev_vocab are left alone since they were
    created by whoever holds their ID range. If prev_vocab is None the
    vocabulary is new and all of its IRIs are checked.
    """
    vocab_name = new_vocab.stem.lower()
    voc = config.IDRANGES.vocabs.get(vocab_name)
    if voc is None:
        logger.debug(
            '-> No ID range config for vocabulary "%s". Cannot check ID usage.',
            vocab_name,
        )
        return

    logger.debug('-> Checking ID usage in "%s" for actor "%s".', new_vocab, actor)

    if not actor:
        msg = (
            f'Cannot check ID usage in "{vocab_name}" because the environment '
            "variable GITHUB_ACTOR is not set."
        )
        if os.getenv("CI_RUN"):
            raise Voc4catError(msg)
        logger.warning("-> %s", msg)
        return

    granted = config.ID_RANGES_BY_ACTOR.get((vocab_name, actor.lower()), [])
    if not granted:
        msg = (
            f'Actor "{actor}" has no ID range for vocabulary "{vocab_name}". '
            "An ID range must be requested before new IRIs can be added."
        )
        raise Voc4catError(msg)

    new_iris = _typed_entity_iris(new_vocab)
    if prev_vocab is not None:
        new_iris -= _typed_entity_iris(prev_vocab)

    forbidden = _iris_with_forbidden_ids(new_iris, vocab_name, granted, actor)
    if forbidden:
        msg = (
            f"{len(forbidden)} new IRI(s) with IDs that are not allowed for "
            f'actor "{actor}" detected. See log for IRIs.'
        )
        raise Voc4catError(msg)
    logger.debug('-> All new IRIs use IDs granted to actor "%s".', actor)


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
        # skos:broader's sh:nodeKind constraint depends on which profile is
        # in effect: the default (vp4cat-5.3) and vocpub-5.2/vp4cat require
        # sh:nodeKind sh:IRI, but vocpub-4.7 has no shape for skos:broader
        # at all, so a --profile vocpub-4.7 run gives no such guarantee.
        # This cast is safe regardless: URIRef/BNode/Literal are all str
        # subclasses, and parent2 below is only compared, tested for set
        # membership, and stringified -- never treated as IRI-specific.
        for parent2 in sorted(
            cast("Iterable[URIRef]", g.objects(concept, SKOS.broader))
        ):
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
