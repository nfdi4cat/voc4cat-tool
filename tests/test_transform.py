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


def test_prov_from_git_skips_untracked(tmp_path, datadir, monkeypatch, caplog):
    """Test that --prov-from-git skips untracked files with a warning."""
    # Initialize git repo but don't add files
    _run_git(["git", "init"], tmp_path)
    _run_git(["git", "config", "user.email", "test@example.com"], tmp_path)
    _run_git(["git", "config", "user.name", "Test User"], tmp_path)

    # Copy and split the turtle file (but don't commit)
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    main_cli(["transform", "--split", "--inplace", str(tmp_path)])
    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")

    monkeypatch.chdir(tmp_path)

    contents_before = {f: f.read_bytes() for f in vocdir.rglob("*.ttl")}

    with caplog.at_level(logging.INFO):
        main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    assert "is not tracked in git" in caplog.text
    assert "Skipping provenance" in caplog.text

    # Verify that untracked files were not modified (no provenance added)
    ttl_files = list(vocdir.rglob("*.ttl"))
    assert len(ttl_files) > 0
    contents_after = {f: f.read_bytes() for f in ttl_files}
    assert contents_after == contents_before


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


def test_prov_from_git_follows_renames(tmp_path, datadir, monkeypatch, caplog):
    """Test that --prov-from-git tracks file history across renames."""
    # Initialize git repo
    _run_git(["git", "init"], tmp_path)
    _run_git(["git", "config", "user.email", "creator@example.com"], tmp_path)
    _run_git(["git", "config", "user.name", "Original Creator"], tmp_path)

    # Copy and split the turtle file
    shutil.copy(datadir / CS_SIMPLE_TURTLE, tmp_path)
    main_cli(["transform", "--split", "--inplace", str(tmp_path)])
    vocdir = (tmp_path / CS_SIMPLE_TURTLE).with_suffix("")

    # Commit the original files with a specific date
    _run_git(["git", "add", "."], tmp_path)
    _run_git(
        ["git", "commit", "-m", "Initial commit", "--date", "2020-01-15T10:00:00"],
        tmp_path,
    )

    # Get one of the concept files from partition
    partition_dirs = [d for d in vocdir.iterdir() if d.is_dir()]
    assert len(partition_dirs) > 0
    partition_dir = partition_dirs[0]
    concept_files = [
        f for f in partition_dir.glob("*.ttl") if f.name != "concept_scheme.ttl"
    ]
    assert len(concept_files) > 0
    old_file = concept_files[0]
    new_filename = "renamed_" + old_file.name
    new_file = partition_dir / new_filename

    # Rename the file using git mv
    old_rel = old_file.relative_to(tmp_path)
    new_rel = new_file.relative_to(tmp_path)
    _run_git(["git", "mv", str(old_rel), str(new_rel)], tmp_path)

    # Change committer for the rename
    _run_git(["git", "config", "user.email", "renamer@example.com"], tmp_path)
    _run_git(["git", "config", "user.name", "File Renamer"], tmp_path)

    # Commit the rename with a different date
    _run_git(
        ["git", "commit", "-m", "Rename file", "--date", "2025-06-15T10:00:00"],
        tmp_path,
    )

    monkeypatch.chdir(tmp_path)

    # Run prov-from-git
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])

    # Parse the renamed file and check dates
    graph = Graph().parse(new_file, format="turtle")
    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))

    # dct:created should be from the ORIGINAL commit (2020-01-15), not the rename
    created = str(next(iter(graph.objects(concept_iri, DCTERMS.created))))
    assert created == "2020-01-15"

    # dct:modified should be from the most recent commit (the rename)
    modified = str(next(iter(graph.objects(concept_iri, DCTERMS.modified))))
    assert modified == "2025-06-15"


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


# ===== Tests for --diff-base option =====


def test_diff_base_unchanged_keeps_dates(git_repo_with_split_files, monkeypatch):
    """Unchanged concept keeps original dates from base version."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Add provenance dates and commit -> this is the "base" state
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance"], repo_path)

    # Record original dates from a concept file
    concept_files = sorted(
        f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    )
    test_file = concept_files[0]
    graph = Graph().parse(test_file, format="turtle")
    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))
    original_created = str(next(iter(graph.objects(concept_iri, DCTERMS.created))))
    original_modified = str(next(iter(graph.objects(concept_iri, DCTERMS.modified))))

    # Simulate CI stripping dates: remove dct:created/modified, re-serialize, commit
    for ttl_file in vocdir.rglob("*.ttl"):
        g = Graph().parse(ttl_file, format="turtle")
        g.remove((None, DCTERMS.created, None))
        g.remove((None, DCTERMS.modified, None))
        g.serialize(destination=ttl_file, format="longturtle")
    _run_git(["git", "add", "."], repo_path)
    _run_git(
        [
            "git",
            "commit",
            "-m",
            "CI strips dates",
            "--date",
            "2030-06-15T10:00:00",
        ],
        repo_path,
    )

    # Run --prov-from-git --diff-base HEAD~1 (compare against base with dates)
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD~1",
            "--inplace",
            str(vocdir),
        ]
    )

    # Content hasn't changed (only dates were stripped), so dates should be restored
    graph2 = Graph().parse(test_file, format="turtle")
    assert (
        str(next(iter(graph2.objects(concept_iri, DCTERMS.created))))
        == original_created
    )
    assert (
        str(next(iter(graph2.objects(concept_iri, DCTERMS.modified))))
        == original_modified
    )


def test_diff_base_changed_gets_git_dates(git_repo_with_split_files, monkeypatch):
    """Changed concept gets dates updated from git history."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Add provenance dates and commit
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance"], repo_path)

    # Get concept files
    concept_files = sorted(
        f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    )
    changed_file = concept_files[0]
    unchanged_file = concept_files[1]

    # Record dates from unchanged file
    graph_unch = Graph().parse(unchanged_file, format="turtle")
    unch_iri = next(iter(graph_unch.subjects(None, SKOS.Concept)))
    unch_created = str(next(iter(graph_unch.objects(unch_iri, DCTERMS.created))))
    unch_modified = str(next(iter(graph_unch.objects(unch_iri, DCTERMS.modified))))

    # Modify the changed file's content (add a new triple)
    graph_ch = Graph().parse(changed_file, format="turtle")
    ch_iri = next(iter(graph_ch.subjects(None, SKOS.Concept)))
    graph_ch.add((ch_iri, SKOS.note, Literal("A new note", lang="en")))
    graph_ch.serialize(destination=changed_file, format="longturtle")

    # Commit the change with a specific date
    _run_git(["git", "add", "."], repo_path)
    _run_git(
        [
            "git",
            "commit",
            "-m",
            "Modify concept",
            "--date",
            "2030-06-15T10:00:00",
        ],
        repo_path,
    )

    # Run --prov-from-git --diff-base HEAD~1
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD~1",
            "--inplace",
            str(vocdir),
        ]
    )

    # Unchanged file should keep base dates
    graph_unch2 = Graph().parse(unchanged_file, format="turtle")
    assert (
        str(next(iter(graph_unch2.objects(unch_iri, DCTERMS.created)))) == unch_created
    )
    assert (
        str(next(iter(graph_unch2.objects(unch_iri, DCTERMS.modified))))
        == unch_modified
    )

    # Changed file should get new git dates (dct:modified from most recent commit)
    graph_ch2 = Graph().parse(changed_file, format="turtle")
    ch_modified = str(next(iter(graph_ch2.objects(ch_iri, DCTERMS.modified))))
    assert ch_modified == "2030-06-15"


def test_diff_base_new_file_gets_git_dates(
    git_repo_with_split_files, monkeypatch, caplog
):
    """New file (not in base ref) gets dates from git history."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Create a new concept file in the partition directory
    partition_dir = vocdir / "IDs0000xxx"
    assert partition_dir.is_dir()

    new_file = partition_dir / "99.ttl"
    new_file.write_text(
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
        "@prefix ex: <http://example.org/> .\n"
        "@prefix dcterms: <http://purl.org/dc/terms/> .\n"
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        "\n"
        "ex:test99 a skos:Concept ;\n"
        '    dcterms:identifier "test99"^^xsd:token ;\n'
        '    skos:definition "A new concept"@en ;\n'
        "    skos:inScheme <http://example.org/test/> ;\n"
        '    skos:prefLabel "new term"@en .\n',
        encoding="utf-8",
    )

    _run_git(["git", "add", "."], repo_path)
    _run_git(
        [
            "git",
            "commit",
            "-m",
            "Add new concept",
            "--date",
            "2030-03-15T10:00:00",
        ],
        repo_path,
    )

    # Run --prov-from-git --diff-base HEAD~1 (new file not in base)
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD~1",
            "--inplace",
            str(vocdir),
        ]
    )

    # New file should get git dates
    graph = Graph().parse(new_file, format="turtle")
    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))
    created = list(graph.objects(concept_iri, DCTERMS.created))
    modified = list(graph.objects(concept_iri, DCTERMS.modified))
    assert len(created) == 1
    assert len(modified) == 1
    assert str(modified[0]) == "2030-03-15"


def test_diff_base_requires_prov_from_git(git_repo_with_split_files, monkeypatch):
    """--diff-base without --prov-from-git raises error."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    with pytest.raises(Voc4catError, match="--diff-base requires --prov-from-git"):
        main_cli(["transform", "--diff-base", "HEAD", "--inplace", str(vocdir)])


def test_diff_base_invalid_ref(git_repo_with_split_files, monkeypatch):
    """Invalid git ref raises Voc4catError."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    with pytest.raises(Voc4catError, match="not a valid git ref"):
        main_cli(
            [
                "transform",
                "--prov-from-git",
                "--diff-base",
                "nonexistent-ref-xyz",
                "--inplace",
                str(vocdir),
            ]
        )


def test_diff_base_base_no_dates_falls_through(git_repo_with_split_files, monkeypatch):
    """If base version has no dates, falls through to git-history logic."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Base state has NO provenance dates (just split files committed)
    # Run --prov-from-git --diff-base HEAD
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD",
            "--inplace",
            str(vocdir),
        ]
    )

    # Content is unchanged, but base has no dates -> falls through to git-history
    concept_files = [f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"]
    graph = Graph().parse(concept_files[0], format="turtle")
    concept_iri = next(iter(graph.subjects(None, SKOS.Concept)))

    # Should have dates from git history (not from base, since base had none)
    created = list(graph.objects(concept_iri, DCTERMS.created))
    modified = list(graph.objects(concept_iri, DCTERMS.modified))
    assert len(created) == 1
    assert len(modified) == 1


def test_diff_base_with_outdir(git_repo_with_split_files, monkeypatch):
    """Works correctly with --outdir (source paths used for git lookups)."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Add provenance and commit
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance"], repo_path)

    # Record dates from a concept file
    concept_files = sorted(
        f for f in vocdir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    )
    test_file = concept_files[0]
    graph_orig = Graph().parse(test_file, format="turtle")
    concept_iri = next(iter(graph_orig.subjects(None, SKOS.Concept)))
    original_created = str(next(iter(graph_orig.objects(concept_iri, DCTERMS.created))))
    original_modified = str(
        next(iter(graph_orig.objects(concept_iri, DCTERMS.modified)))
    )

    outdir = repo_path / "output"
    outdir.mkdir()

    # Run with --outdir and --diff-base HEAD (unchanged)
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD",
            "--outdir",
            str(outdir),
            str(vocdir),
        ]
    )

    # Check output directory has files with restored dates
    target_dir = outdir / vocdir.name
    assert target_dir.is_dir()

    copied_concept_files = sorted(
        f for f in target_dir.rglob("*.ttl") if f.name != "concept_scheme.ttl"
    )
    assert len(copied_concept_files) > 0

    # Dates should match the base (HEAD) since content is unchanged
    graph_copy = Graph().parse(copied_concept_files[0], format="turtle")
    assert (
        str(next(iter(graph_copy.objects(concept_iri, DCTERMS.created))))
        == original_created
    )
    assert (
        str(next(iter(graph_copy.objects(concept_iri, DCTERMS.modified))))
        == original_modified
    )


def test_diff_base_concept_scheme(git_repo_with_split_files, monkeypatch):
    """Handles concept_scheme.ttl (with Person/Organization entities)."""
    repo_path, vocdir = git_repo_with_split_files
    monkeypatch.chdir(repo_path)

    # Add provenance and commit
    main_cli(["transform", "--prov-from-git", "--inplace", str(vocdir)])
    _run_git(["git", "add", "."], repo_path)
    _run_git(["git", "commit", "-m", "Add provenance"], repo_path)

    cs_file = vocdir / "concept_scheme.ttl"
    assert cs_file.exists()

    # Record concept scheme dates
    graph = Graph().parse(cs_file, format="turtle")
    cs_iri = next(iter(graph.subjects(None, SKOS.ConceptScheme)))
    original_created = str(next(iter(graph.objects(cs_iri, DCTERMS.created))))
    original_modified = str(next(iter(graph.objects(cs_iri, DCTERMS.modified))))

    # Run --prov-from-git --diff-base HEAD (unchanged)
    main_cli(
        [
            "transform",
            "--prov-from-git",
            "--diff-base",
            "HEAD",
            "--inplace",
            str(vocdir),
        ]
    )

    # concept_scheme.ttl should be handled correctly (dates restored from base)
    graph2 = Graph().parse(cs_file, format="turtle")
    assert str(next(iter(graph2.objects(cs_iri, DCTERMS.created)))) == original_created
    assert (
        str(next(iter(graph2.objects(cs_iri, DCTERMS.modified)))) == original_modified
    )
