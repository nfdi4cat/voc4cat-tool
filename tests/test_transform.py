import logging
import os
import shutil
from unittest import mock

import pytest
from rdflib import DCTERMS, OWL, SKOS, XSD, Graph, Literal

from tests.test_cli import CS_CYCLES
from voc4cat.checks import Voc4catError
from voc4cat.cli import main_cli
from voc4cat.transform import _run_git, get_partition_dir_name

CS_SIMPLE_TURTLE = "concept-scheme-simple.ttl"

# ===== Tests for no option set =====


def test_transform_no_option(monkeypatch, datadir, tmp_path, caplog, cs_cycles_xlsx):
    shutil.copy(cs_cycles_xlsx, tmp_path / CS_CYCLES)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", str(tmp_path)])
    assert "nothing to do for xlsx files" in caplog.text

    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path / CS_SIMPLE_TURTLE)
    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", str(tmp_path)])
    assert "nothing to do for rdf files" in caplog.text


def test_transform_unsupported_filetype(monkeypatch, datadir, tmp_path, caplog):
    shutil.copy(datadir / "README.md", tmp_path)
    monkeypatch.chdir(tmp_path)
    # Try to run a command that would overwrite the input file with the output file
    with caplog.at_level(logging.WARNING):
        main_cli(["transform", str(tmp_path / "README.md")])
    assert "Unsupported filetype: " in caplog.text


# ===== Tests for options --split / --join =====


@pytest.mark.parametrize(
    "opt",
    [None, "--inplace"],
    ids=["default", "inplace"],
)
def test_split(monkeypatch, datadir, tmp_path, opt, caplog):
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    cmd = ["transform", "-v", "--split"]
    if opt:
        cmd.append("--inplace")
    cmd.append(str(tmp_path))
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> wrote split vocabulary to" in caplog.text

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")
    assert vocdir.is_dir()
    assert (vocdir / "concept_scheme.ttl").exists()
    assert len([*vocdir.rglob("*.ttl")]) == 8  # Use rglob for partitioned structure
    if opt:
        assert not (tmp_path / CS_SIMPLE_TURTLE).exists()


@pytest.mark.parametrize(
    "opt",
    [None, "inplace", "outdir"],
)
def test_join(monkeypatch, datadir, tmp_path, opt, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    if opt == "inplace":
        cmd.append("--inplace")
    elif opt == "outdir":
        cmd.append("--outdir")
        cmd.append(str(tmp_path / "outdir"))
    cmd.append(str(tmp_path))

    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> joined vocabulary into" in caplog.text

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")
    if opt == "inplace":
        assert not vocdir.exists()
        assert (vocdir.parent / CS_SIMPLE_TURTLE).exists()
    elif opt == "outdir":
        assert (tmp_path / "outdir" / CS_SIMPLE_TURTLE).exists()
        assert not (vocdir.parent / CS_SIMPLE_TURTLE).exists()
    else:
        assert (vocdir.parent / CS_SIMPLE_TURTLE).exists()


@mock.patch.dict(
    os.environ, {"CI": "", "VOC4CAT_VERSION": "v2.0", "VOC4CAT_MODIFIED": "2023-08-15"}
)
def test_join_with_envvars(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    cmd.append(str(tmp_path))
    with caplog.at_level(logging.DEBUG):
        main_cli(cmd)
    assert "-> joined vocabulary into" in caplog.text
    # Were version and modified date correctly set?
    graph = Graph().parse(CS_SIMPLE_TURTLE, format="turtle")
    cs_query = "SELECT ?iri WHERE {?iri a skos:ConceptScheme.}"
    qresults = [*graph.query(cs_query, initNs={"skos": SKOS})]
    assert len(qresults) == 1

    cs_iri = qresults[0][0]
    assert (
        len(
            [
                *graph.triples(
                    (cs_iri, OWL.versionInfo, Literal("v2.0")),
                )
            ]
        )
        == 1
    )

    assert (
        len(
            [
                *graph.triples(
                    (
                        cs_iri,
                        DCTERMS.modified,
                        Literal("2023-08-15", datatype=XSD.date),
                    ),
                )
            ]
        )
        == 1
    )


@mock.patch.dict(
    os.environ, {"CI": "", "VOC4CAT_VERSION": "2.0", "VOC4CAT_MODIFIED": "2023-08-15"}
)
def test_join_with_invalid_envvar(monkeypatch, datadir, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    # create dir with split files
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    # join files again as test
    cmd = ["transform", "-v", "--join"]
    cmd.append(str(tmp_path))
    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(
            Voc4catError, match="Invalid environment variable VOC4CAT_VERSION"
        ),
    ):
        main_cli(cmd)
    assert 'Invalid environment variable VOC4CAT_VERSION "2.0"' in caplog.text


# ===== Tests for option --prov-from-git =====


@pytest.fixture
def git_repo_with_split_files(tmp_path, datadir):
    """Create a git repo with split turtle files."""
    # Initialize git repo
    _run_git(["git", "init"], tmp_path)
    _run_git(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run_git(["git", "config", "user.name", "Test User"], tmp_path)

    # Copy and split the turtle file
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    main_cli(["transform", "--split", "--inplace", str(tmp_path)])

    # The split files are in a subdirectory
    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")

    # Add and commit the split files
    _run_git(["git", "add", "."], tmp_path)
    _run_git(["git", "commit", "-m", "Initial commit"], tmp_path)

    return tmp_path, vocdir


def test_prov_from_git_adds_dates(git_repo_with_split_files, monkeypatch, caplog):
    """Test that --prov-from-git adds dct:created and dct:modified."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    with caplog.at_level(logging.INFO):
        main_cli(["transform", "-v", "--prov-from-git", "--inplace", str(vocdir)])
    assert "-> added provenance from git to" in caplog.text

    # Check that dct:created and dct:modified were added to a concept file
    # Use rglob to find files in partitioned subdirectories
    concept_files = [f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"]
    assert len(concept_files) > 0

    graph = Graph().parse(concept_files[0], format="turtle")
    concepts = list(graph.subjects(None, SKOS.Concept))
    assert len(concepts) == 1
    concept_iri = concepts[0]

    # Check dct:created exists
    created_values = list(graph.objects(concept_iri, DCTERMS.created))
    assert len(created_values) == 1

    # Check dct:modified exists
    modified_values = list(graph.objects(concept_iri, DCTERMS.modified))
    assert len(modified_values) == 1


def test_prov_from_git_error_untracked(tmp_path, datadir, monkeypatch, caplog):
    """Test that --prov-from-git fails if files are not tracked in git."""
    # Initialize git repo but don't add files
    _run_git(["git", "init"], tmp_path)
    _run_git(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run_git(["git", "config", "user.name", "Test User"], tmp_path)

    # Copy and split the turtle file (but don't commit)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    main_cli(["transform", "--split", "--inplace", str(tmp_path)])
    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")

    monkeypatch.chdir(tmp_path)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(Voc4catError, match="is not tracked in git"),
    ):
        main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])


def test_prov_from_git_error_not_directory(tmp_path, datadir, monkeypatch, caplog):
    """Test that --prov-from-git fails if input is not a directory with .ttl files."""
    # Initialize git repo
    _run_git(["git", "init"], tmp_path)

    # Copy a single turtle file (not split)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)

    monkeypatch.chdir(tmp_path)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(Voc4catError, match="--prov-from-git requires a directory"),
    ):
        main_cli(
            [
                "transform",
                "--prov-from-git",
                "--inplace",
                str(tmp_path / CS_SIMPLE_TURTLE),
            ]
        )


def test_prov_from_git_preserves_existing_created(
    git_repo_with_split_files, monkeypatch, caplog
):
    """Test that --prov-from-git preserves existing dct:created."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # First, add provenance
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    # Modify a file to add a custom dct:created date
    # Use rglob to find files in partitioned subdirectories
    concept_files = [f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"]
    test_file = concept_files[0]
    graph = Graph().parse(test_file, format="turtle")

    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))
    original_created = next(iter(graph.objects(concept_iri, DCTERMS.created)))

    # Commit the changes so git sees a modification
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance", "."], repo_path)

    # Run again - dct:created should not change
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    graph2 = Graph().parse(test_file, format="turtle")
    created_after = next(iter(graph2.objects(concept_iri, DCTERMS.created)))

    assert str(original_created) == str(created_after)


def test_prov_from_git_updates_modified(git_repo_with_split_files, monkeypatch, caplog):
    """Test that --prov-from-git updates dct:modified when it differs from git."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # First, add provenance
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    # Commit the changes so git sees a modification
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance", "."], repo_path)

    # Manually set a different dct:modified date in the file
    # (simulating an old date that differs from the current git modified date)
    # Use rglob to find files in partitioned subdirectories
    concept_files = [f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"]
    test_file = concept_files[0]
    graph = Graph().parse(test_file, format="turtle")

    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))

    # Remove existing dct:modified and add an old date
    graph.remove((concept_iri, DCTERMS.modified, None))
    old_date = "2020-01-01"
    graph.add((concept_iri, DCTERMS.modified, Literal(old_date, datatype=XSD.date)))
    graph.serialize(destination=test_file, format="longturtle")

    # Commit the change with the old date
    # Commit the changes so git sees a modification
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Set old modified date", "."], repo_path)

    # Run again - dct:modified should update from 2020-01-01 to today's git commit date
    with caplog.at_level(logging.INFO):
        main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    # Check log message for update
    assert "Updated dct:modified" in caplog.text
    assert old_date in caplog.text  # The old date should be mentioned in the log


def test_prov_from_git_error_no_inplace_or_outdir(
    git_repo_with_split_files, monkeypatch, caplog
):
    """Test that --prov-from-git fails without --inplace or --outdir."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(Voc4catError, match="requires either --inplace or --outdir"),
    ):
        main_cli(["transform", "--prov-from-git", str(vocdir)])


def test_prov_from_git_with_outdir(git_repo_with_split_files, monkeypatch, caplog):
    """Test that --prov-from-git with --outdir copies files to output directory."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    outdir = repo_path / "output"
    outdir.mkdir()

    with caplog.at_level(logging.INFO):
        main_cli(["transform", "--prov-from-git", "--outdir", str(outdir), str(vocdir)])
    assert "-> added provenance from git to" in caplog.text

    # Check that files were copied to outdir
    target_dir = outdir / vocdir.name
    assert target_dir.is_dir()
    assert (target_dir / "concept_scheme.ttl").exists()

    # Check that original files were NOT modified (no dct:created/modified)
    # Use rglob to find files in partitioned subdirectories
    original_concept_files = [
        f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    ]
    graph_original = Graph().parse(original_concept_files[0], format="turtle")
    concept_iri = next(iter(graph_original.subjects(None, SKOS.Concept)))
    assert len(list(graph_original.objects(concept_iri, DCTERMS.created))) == 0

    # Check that copied files HAVE dct:created/modified
    # Use rglob to find files in partitioned subdirectories
    copied_concept_files = [
        f for f in target_dir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    ]
    graph_copied = Graph().parse(copied_concept_files[0], format="turtle")
    concept_iri_copied = next(iter(graph_copied.subjects(None, SKOS.Concept)))
    assert len(list(graph_copied.objects(concept_iri_copied, DCTERMS.created))) == 1
    assert len(list(graph_copied.objects(concept_iri_copied, DCTERMS.modified))) == 1


def test_prov_from_git_parent_directory(git_repo_with_split_files, monkeypatch, caplog):
    """Test that --prov-from-git works with a parent directory containing vocab subdirs."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Pass the parent directory (repo_path) instead of the specific vocab directory
    with caplog.at_level(logging.INFO):
        main_cli(["transform", "-v", "--prov-from-git", "--inplace", str(repo_path)])
    assert "-> added provenance from git to" in caplog.text

    # Check that dct:created and dct:modified were added to a concept file
    # Use rglob to find files in partitioned subdirectories
    concept_files = [f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"]
    assert len(concept_files) > 0

    graph = Graph().parse(concept_files[0], format="turtle")
    concepts = list(graph.subjects(None, SKOS.Concept))
    assert len(concepts) == 1
    concept_iri = concepts[0]

    # Check dct:created exists
    created_values = list(graph.objects(concept_iri, DCTERMS.created))
    assert len(created_values) == 1

    # Check dct:modified exists
    modified_values = list(graph.objects(concept_iri, DCTERMS.modified))
    assert len(modified_values) == 1


# ===== Tests for partitioned split structure =====


@pytest.mark.parametrize(
    ("numeric_id", "id_length", "expected"),
    [
        # 7-digit IDs (default)
        ("0000000", 7, "IDs0000xxx"),
        ("0000001", 7, "IDs0000xxx"),
        ("0000042", 7, "IDs0000xxx"),
        ("0000999", 7, "IDs0000xxx"),
        ("0001000", 7, "IDs0001xxx"),
        ("0001001", 7, "IDs0001xxx"),
        ("0001500", 7, "IDs0001xxx"),
        ("0001999", 7, "IDs0001xxx"),
        ("0002000", 7, "IDs0002xxx"),
        ("0007017", 7, "IDs0007xxx"),
        ("0999999", 7, "IDs0999xxx"),
        # 6-digit IDs
        ("000000", 6, "IDs000xxx"),
        ("000001", 6, "IDs000xxx"),
        ("000042", 6, "IDs000xxx"),
        ("000999", 6, "IDs000xxx"),
        ("001000", 6, "IDs001xxx"),
        ("001500", 6, "IDs001xxx"),
        ("007017", 6, "IDs007xxx"),
        # 5-digit IDs
        ("00000", 5, "IDs00xxx"),
        ("00042", 5, "IDs00xxx"),
        ("00999", 5, "IDs00xxx"),
        ("01000", 5, "IDs01xxx"),
        # Edge case: empty string
        ("", 7, "IDs0000xxx"),
    ],
)
def test_get_partition_dir_name(numeric_id, id_length, expected):
    """Test partition directory name calculation for various ID lengths."""
    assert get_partition_dir_name(numeric_id, id_length) == expected


def test_split_creates_partitioned_structure(monkeypatch, datadir, tmp_path, caplog):
    """Test that split creates IDs{NNN}xxx subdirectories based on ID ranges."""
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])
    assert "-> wrote split vocabulary to" in caplog.text

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")
    assert vocdir.is_dir()

    # concept_scheme.ttl should be in root
    assert (vocdir / "concept_scheme.ttl").exists()

    # Concept files should be in partition subdirectories
    # The test data has concepts with small IDs (01-06) and a collection (10)
    # All should be in IDs0000xxx for 7-digit IDs (default)
    partition_dir = vocdir / "IDs0000xxx"
    assert partition_dir.is_dir()

    # Count total .ttl files (should be same as before: concept_scheme + 7 entities)
    all_ttl_files = list(vocdir.rglob("*.ttl"))
    assert len(all_ttl_files) == 8

    # concept_scheme.ttl in root, 7 entity files in partition dir
    assert len(list(partition_dir.glob("*.ttl"))) == 7


def test_join_partitioned_structure(monkeypatch, datadir, tmp_path, caplog):
    """Test that join works with partitioned IDs{NNN}xxx subdirectory structure."""
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    monkeypatch.chdir(tmp_path)

    # First split to create partitioned structure
    main_cli(["transform", "-v", "--split", "--inplace", str(tmp_path)])

    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")

    # Verify partitioned structure was created
    partition_dir = vocdir / "IDs0000xxx"
    assert partition_dir.is_dir()

    # Now join the partitioned structure
    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", "-v", "--join", "--inplace", str(tmp_path)])
    assert "-> joined vocabulary into" in caplog.text

    # The split directory should be removed (--inplace)
    assert not vocdir.exists()

    # The joined file should exist
    assert (tmp_path / CS_SIMPLE_TURTLE).exists()

    # Verify the joined file contains all expected content
    graph = Graph().parse(tmp_path / CS_SIMPLE_TURTLE, format="turtle")
    concepts = list(graph.subjects(None, SKOS.Concept))
    collections = list(graph.subjects(None, SKOS.Collection))
    schemes = list(graph.subjects(None, SKOS.ConceptScheme))

    # Original test data has 6 concepts, 1 collection, 1 concept scheme
    assert len(concepts) == 6
    assert len(collections) == 1
    assert len(schemes) == 1


def test_join_flat_structure_backward_compat(monkeypatch, datadir, tmp_path, caplog):
    """Test that join still works with old flat structure (backward compatibility)."""
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    monkeypatch.chdir(tmp_path)

    # Create a flat structure manually (simulate old format)
    vocdir = tmp_path / "flat-vocab"
    vocdir.mkdir()

    # Parse the source file and create flat split manually
    source_graph = Graph().parse(tmp_path / CS_SIMPLE_TURTLE, format="turtle")

    # Extract concept scheme
    cs_graph = Graph()
    for cs_iri in source_graph.subjects(None, SKOS.ConceptScheme):
        for triple in source_graph.triples((cs_iri, None, None)):
            cs_graph.add(triple)
    cs_graph.serialize(destination=vocdir / "concept_scheme.ttl", format="turtle")

    # Extract concepts (flat, no subdirectories)
    for concept_iri in source_graph.subjects(None, SKOS.Concept):
        concept_graph = Graph()
        for triple in source_graph.triples((concept_iri, None, None)):
            concept_graph.add(triple)
        # Extract ID from IRI for filename
        iri_str = str(concept_iri)
        numeric_id = "".join(c for c in reversed(iri_str) if c.isdigit())[::-1]
        if numeric_id:
            concept_graph.serialize(
                destination=vocdir / f"{numeric_id}.ttl", format="turtle"
            )

    # Now join the flat structure
    with caplog.at_level(logging.DEBUG):
        main_cli(["transform", "-v", "--join", str(tmp_path)])
    assert "-> joined vocabulary into" in caplog.text

    # The joined file should exist
    assert (tmp_path / "flat-vocab.ttl").exists()
