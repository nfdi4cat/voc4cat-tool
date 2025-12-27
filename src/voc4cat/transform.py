import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import DCTERMS, OWL, RDF, SDO, SKOS, XSD, Graph, Literal

if sys.version_info < (3, 11):
    import isodate

from voc4cat.checks import Voc4catError
from voc4cat.utils import EXCEL_FILE_ENDINGS, RDF_FILE_ENDINGS

logger = logging.getLogger(__name__)


def _run_git(cmd: list[str], repo_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run a constrained git command in a repo directory."""
    if not cmd or cmd[0] != "git":
        msg = "Only 'git' commands are allowed."
        raise Voc4catError(msg)
    if shutil.which("git") is None:
        msg = "git executable not found in PATH."
        raise Voc4catError(msg)
    return subprocess.run(  # noqa: S603
        cmd,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def _repo_relative_path(path: Path, repo_dir: Path) -> str:
    """Return a repo-relative POSIX path and reject paths outside the repo."""
    repo_dir = repo_dir.resolve()
    path = path if path.is_absolute() else (repo_dir / path)
    path = path.resolve()
    try:
        rel = path.relative_to(repo_dir)
    except ValueError as exc:
        msg = f'Path "{path}" is outside git repo "{repo_dir}".'
        raise Voc4catError(msg) from exc
    return rel.as_posix()


# ===== Git history utilities =====


@dataclass
class FileGitInfo:
    """Git history information for a file."""

    created_by: str = ""
    created_email: str = ""
    created_at: datetime = None
    modified_by: str = ""
    modified_email: str = ""
    modified_at: datetime = None


def get_directory_git_info(
    directory: Path, repo_dir: Path | None = None
) -> dict[str, FileGitInfo]:
    """Get git info for all tracked files in a directory.

    Args:
        directory: Directory containing files to get git info for.
        repo_dir: Git repository root directory. Defaults to current working directory.

    Returns:
        Dictionary mapping file paths (relative to repo_dir) to FileGitInfo objects.
    """
    repo_dir = Path(repo_dir) if repo_dir else Path.cwd()
    directory = Path(directory)

    # Step 1: Get all tracked files in the directory (validate directory is within repo)
    rel_directory = _repo_relative_path(directory, repo_dir)
    ls_cmd = ["git", "ls-files", "--", rel_directory]
    ls_result = _run_git(ls_cmd, repo_dir)

    filepaths = [f for f in ls_result.stdout.strip().split("\n") if f]
    if not filepaths:
        return {}

    # Step 2: Get history for all files in one call
    log_cmd = [
        "git",
        "log",
        "--format=COMMIT%x00%an%x00%ae%x00%aI",
        "--name-only",
        "--",
        *filepaths,
    ]
    log_result = _run_git(log_cmd, repo_dir)

    # Parse: track first and last commit per file
    first_commit = {}  # oldest
    last_commit = {}  # most recent
    current_commit = None

    for iline in log_result.stdout.split("\n"):
        line = iline.strip()
        if not line:
            continue

        if line.startswith("COMMIT\x00"):
            _, name, email, date_str = line.split("\x00")
            if sys.version_info >= (3, 11):
                date_commit = datetime.fromisoformat(date_str)
            else:
                date_commit = isodate.parse_datetime(date_str)
            current_commit = (name, email, date_commit)
        else:
            # Filename - log outputs newest→oldest
            first_commit[line] = current_commit  # keeps getting overwritten → oldest
            if line not in last_commit:
                last_commit[line] = current_commit  # first seen → most recent

    # Build results
    return {
        fp: FileGitInfo(
            created_by=first_commit[fp][0],
            created_email=first_commit[fp][1],
            created_at=first_commit[fp][2],
            modified_by=last_commit[fp][0],
            modified_email=last_commit[fp][1],
            modified_at=last_commit[fp][2],
        )
        for fp in filepaths
        if fp in first_commit
    }


def add_prov_from_git(
    vocab_dir: Path, repo_dir: Path | None = None, source_dir: Path | None = None
) -> None:
    """Add dct:created and dct:modified to RDF files based on git history.

    For each .ttl file in vocab_dir:
    - dct:created: Add only if missing (from git first commit date)
    - dct:modified: Update if different from git last commit date (logs info message)

    Args:
        vocab_dir: Directory containing split turtle files to modify.
        repo_dir: Git repository root directory. Defaults to current working directory.
        source_dir: Directory to look up git history from (if different from vocab_dir).
            Used when files have been copied to a new location.

    Raises:
        Voc4catError: If any .ttl file is not tracked in git.
    """
    repo_dir = Path(repo_dir) if repo_dir else Path.cwd()
    vocab_dir = Path(vocab_dir)
    git_lookup_dir = Path(source_dir) if source_dir else vocab_dir

    # Get all .ttl files in the directory
    ttl_files = list(vocab_dir.glob("*.ttl"))
    if not ttl_files:
        logger.warning("No .ttl files found in %s", vocab_dir)
        return

    # Get git info from the source directory (or vocab_dir if no source specified)
    git_info = get_directory_git_info(git_lookup_dir, repo_dir)

    # Check that all .ttl files are tracked in git (by filename)
    for ttl_file in ttl_files:
        # Build the path as it would appear in the source directory
        source_file = git_lookup_dir / ttl_file.name
        try:
            rel_path = source_file.relative_to(repo_dir)
        except ValueError:
            rel_path = source_file
        # Normalize path separators (git uses forward slashes)
        rel_path_str = str(rel_path).replace("\\", "/")
        if rel_path_str not in git_info:
            msg = f'File "{ttl_file}" is not tracked in git. Cannot add provenance.'
            raise Voc4catError(msg)

    # Process each .ttl file
    for ttl_file in ttl_files:
        # Build the path as it would appear in the source directory for git lookup
        source_file = git_lookup_dir / ttl_file.name
        try:
            rel_path = source_file.relative_to(repo_dir)
        except ValueError:
            rel_path = source_file
        rel_path_str = str(rel_path).replace("\\", "/")
        info = git_info[rel_path_str]

        # Parse the RDF graph
        graph = Graph().parse(ttl_file, format="turtle")

        # Find the main subject IRI (concept, collection, or concept scheme)
        main_iri = None
        for rdf_type in [SKOS.Concept, SKOS.Collection, SKOS.ConceptScheme]:
            subjects = list(graph.subjects(RDF.type, rdf_type))
            if subjects:
                main_iri = subjects[0]
                break

        if main_iri is None:
            logger.warning("No SKOS entity found in %s, skipping.", ttl_file)
            continue

        modified = False

        # Handle dct:created - add only if missing
        existing_created = list(graph.objects(main_iri, DCTERMS.created))
        if not existing_created:
            created_date = info.created_at.strftime("%Y-%m-%d")
            graph.add(
                (main_iri, DCTERMS.created, Literal(created_date, datatype=XSD.date))
            )
            logger.debug("Added dct:created=%s to %s", created_date, ttl_file.name)
            modified = True

        # Handle dct:modified - update if different
        git_modified_date = info.modified_at.strftime("%Y-%m-%d")
        existing_modified = list(graph.objects(main_iri, DCTERMS.modified))
        if existing_modified:
            existing_date = str(existing_modified[0])
            if existing_date != git_modified_date:
                graph.remove((main_iri, DCTERMS.modified, None))
                graph.add(
                    (
                        main_iri,
                        DCTERMS.modified,
                        Literal(git_modified_date, datatype=XSD.date),
                    )
                )
                logger.info(
                    "Updated dct:modified in %s: %s -> %s",
                    ttl_file.name,
                    existing_date,
                    git_modified_date,
                )
                modified = True
        else:
            graph.add(
                (
                    main_iri,
                    DCTERMS.modified,
                    Literal(git_modified_date, datatype=XSD.date),
                )
            )
            logger.debug(
                "Added dct:modified=%s to %s", git_modified_date, ttl_file.name
            )
            modified = True

        # Serialize back to file if modified
        if modified:
            graph.serialize(destination=ttl_file, format="longturtle")


# ===== Split/join utilities =====


def extract_numeric_id_from_iri(iri):
    iri_path = urlsplit(iri).path
    reverse_id = []
    for char in reversed(iri_path):  # pragma: no branch
        if char.isdigit():
            reverse_id.append(char)
        elif char == "/":
            continue
        else:
            break
    return "".join(reversed(reverse_id))


def write_split_turtle(vocab_graph: Graph, outdir: Path) -> None:
    """
    Write each concept, collection and concept scheme to a separate turtle file.

    The ids are used as filenames. Schema:Person and schema:Organization entities
    are included in the concept_scheme.ttl file.
    """
    outdir.mkdir(exist_ok=True)
    query = "SELECT ?iri WHERE {?iri a %s.}"

    for skos_class in ["skos:Concept", "skos:Collection", "skos:ConceptScheme"]:
        qresults = vocab_graph.query(query % skos_class, initNs={"skos": SKOS})
        # Iterate over search results and write each concept, collection and
        # concept scheme to a separate turtle file using id as filename.
        for qresult in qresults:
            iri = qresult["iri"]
            tmp_graph = Graph()
            tmp_graph += vocab_graph.triples((iri, None, None))
            id_part = extract_numeric_id_from_iri(iri)
            if skos_class == "skos:ConceptScheme":
                # Include schema:Person and schema:Organization entities
                # in the concept scheme file (metadata related to scheme)
                for entity_type in [SDO.Person, SDO.Organization]:
                    for entity_iri in vocab_graph.subjects(RDF.type, entity_type):
                        tmp_graph += vocab_graph.triples((entity_iri, None, None))
                outfile = outdir / "concept_scheme.ttl"
            else:
                outfile = outdir / f"{id_part}.ttl"
            tmp_graph.serialize(destination=outfile, format="longturtle")
        logger.debug("-> wrote %i %ss-file(s).", len(qresults), skos_class)


def autoversion_cs(graph: Graph) -> Graph:
    """Set modified date and version if "requested" via environment variables."""
    if any(graph.triples((None, RDF.type, SKOS.ConceptScheme))):  # pragma: no branch
        cs, _, _ = next(graph.triples((None, RDF.type, SKOS.ConceptScheme)))
    if os.getenv("VOC4CAT_MODIFIED") is not None:
        graph.remove((None, DCTERMS.modified, None))
        date_modified = os.getenv("VOC4CAT_MODIFIED")
        graph.add((cs, DCTERMS.modified, Literal(date_modified, datatype=XSD.date)))
    if os.getenv("VOC4CAT_VERSION") is not None:
        version = os.getenv("VOC4CAT_VERSION")
        if version is not None and not version.startswith("v"):
            msg = 'Invalid environment variable VOC4CAT_VERSION "%s". Version must start with letter "v".'
            logger.error(msg, version)
            raise Voc4catError(msg % version)
        graph.remove((None, OWL.versionInfo, None))
        graph.add(
            (cs, OWL.versionInfo, Literal(version)),
        )
    return graph


def join_split_turtle(vocab_dir: Path) -> Graph:
    """Join split turtle files back into a single graph.

    The schema:Person and schema:Organization entities are included in
    concept_scheme.ttl and will be joined automatically.
    """
    # Search recursively all turtle files belonging to the concept scheme
    turtle_files = vocab_dir.rglob("*.ttl")
    # Create an empty RDF graph to hold the concept scheme
    cs_graph = Graph()
    # Load each turtle file into a separate graph and merge it into the concept scheme graph
    for file in turtle_files:
        graph = Graph().parse(file, format="turtle")
        # Set modified date if "requested" via environment variable.
        if file.name == "concept_scheme.ttl" or any(
            graph.triples((None, RDF.type, SKOS.ConceptScheme))
        ):
            graph = autoversion_cs(graph)
        cs_graph += graph

    return cs_graph


# ===== transform command & helpers to validate cmd options =====


def _transform_rdf(file, args):
    if args.split:
        vocab_graph = Graph().parse(str(file), format=RDF_FILE_ENDINGS[file.suffix])
        vocab_dir = (
            args.outdir / file.with_suffix("").name
            if args.outdir
            else file.with_suffix("")
        )
        vocab_dir.mkdir(exist_ok=True)
        write_split_turtle(vocab_graph, vocab_dir)
        logger.info("-> wrote split vocabulary to: %s", vocab_dir)
        if args.inplace:
            logger.debug("-> going to remove %s", file)
            file.unlink()
    else:
        logger.debug("-> nothing to do for rdf files!")


def transform(args):
    logger.debug("Transform subcommand started!")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    xlsx_files = [f for f in files if f.suffix.lower() in EXCEL_FILE_ENDINGS]

    rdf_files = [f for f in files if f.suffix.lower() in RDF_FILE_ENDINGS]

    if args.VOCAB.is_file() and (len(xlsx_files) + len(rdf_files)) == 0:
        logger.warning("Unsupported filetype: %s", args.VOCAB)

    if args.join:
        rdf_dirs = [d for d in Path(args.VOCAB).iterdir() if any(d.glob("*.ttl"))]
    else:
        rdf_dirs = []

    for file in xlsx_files:
        logger.debug('Processing "%s"', file)
        logger.debug("-> nothing to do for xlsx files!")

    for file in rdf_files:
        logger.debug('Processing "%s"', file)
        _transform_rdf(file, args)

    for rdf_dir in rdf_dirs:
        logger.debug('Processing rdf files in "%s"', rdf_dir)
        # The if..else is not required now. It is a frame for future additions.
        if args.join:
            vocab_graph = join_split_turtle(rdf_dir)
            dest = (
                (args.outdir / rdf_dir.name).with_suffix(".ttl")
                if args.outdir
                else rdf_dir.with_suffix(".ttl")
            )
            vocab_graph.serialize(destination=str(dest), format="turtle")
            logger.info("-> joined vocabulary into: %s", dest)
            if args.inplace:
                logger.debug("-> going to remove %s", rdf_dir)
                shutil.rmtree(rdf_dir, ignore_errors=True)
        else:  # pragma: no cover
            logger.debug("-> nothing to do!")

    # Handle --prov-from-git option
    if getattr(args, "prov_from_git", False):
        if not args.inplace and not args.outdir:
            msg = "--prov-from-git requires either --inplace or --outdir"
            logger.error(msg)
            raise Voc4catError(msg)

        if not args.VOCAB.is_dir():
            msg = f'--prov-from-git requires a directory, got: "{args.VOCAB}"'
            logger.error(msg)
            raise Voc4catError(msg)

        # Determine vocabulary directories to process:
        # - If VOCAB contains .ttl files directly, it's a single vocabulary directory
        # - Otherwise, look for subdirectories containing .ttl files (like vocabularies/)
        if any(args.VOCAB.glob("*.ttl")):
            vocab_dirs = [args.VOCAB]
        else:
            vocab_dirs = [
                d for d in args.VOCAB.iterdir() if d.is_dir() and any(d.glob("*.ttl"))
            ]
            if not vocab_dirs:
                msg = f'--prov-from-git requires a directory with .ttl files or subdirectories containing .ttl files, got: "{args.VOCAB}"'
                logger.error(msg)
                raise Voc4catError(msg)

        for vocab_dir in vocab_dirs:
            if args.outdir:
                # Copy directory to outdir, then modify the copy
                target_dir = args.outdir / vocab_dir.name
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(vocab_dir, target_dir)
                logger.debug("Copied %s to %s", vocab_dir, target_dir)
                # Pass source_dir so git lookup uses original files
                add_prov_from_git(target_dir, source_dir=vocab_dir)
                logger.info("-> added provenance from git to: %s", target_dir)
            else:
                # --inplace: modify files in place
                logger.debug("Adding provenance from git to %s", vocab_dir)
                add_prov_from_git(vocab_dir)
                logger.info("-> added provenance from git to: %s", vocab_dir)
