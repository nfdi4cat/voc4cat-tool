import logging
import os
from pathlib import Path

from voc4cat import config
from voc4cat.gh_index import build_multirelease_index

logger = logging.getLogger(__name__)


def run_pylode(turtle_file: Path, output_path: Path) -> None:
    """
    Generate pyLODE documentation.
    """
    import pylode

    filename = Path(turtle_file)  # .resolve())
    outdir = output_path / filename.stem
    outdir.mkdir(exist_ok=True)
    outfile = outdir / "index.html"
    # breakpoint()
    html = pylode.MakeDocco(
        # we use str(abs path) because pyLODE 2.x does not find the file otherwise
        input_data_file=str(filename.resolve()),
        outputformat="html",
        profile="vocpub",
    )
    html.document(destination=outfile)
    # Fix html-doc: Do not show overview section with black div for image.
    with open(outfile) as html_file:
        content = html_file.read()
    content = content.replace(
        '<section id="overview">',
        '<section id="overview" style="display: none;">',
    )
    content = content.replace(
        "<dt>Ontology RDF</dt>",
        "<dt>Vocabulary RDF</dt>",
    )
    content = content.replace(
        f'<dd><a href="{filename.stem}.ttl">RDF (turtle)</a></dd>',
        f'<dd><a href="../{filename.stem}.ttl">RDF (turtle)</a></dd>',
    )
    with open(outfile, "w") as html_file:
        html_file.write(content)

    logger.info("-> built pyLODE documentation for %s", turtle_file)


def run_ontospy(turtle_file: Path, output_path: Path) -> None:
    """
    Generate ontospy documentation (single-page html & dendrogram).
    """
    import ontospy
    from ontospy.gendocs.viz.viz_d3dendogram import Dataviz
    from ontospy.gendocs.viz.viz_html_single import HTMLVisualizer

    title = config.VOCAB_TITLE

    specific_output_path = (Path(output_path) / Path(turtle_file).stem).resolve()

    g = ontospy.Ontospy(Path(turtle_file).resolve().as_uri())

    docs = HTMLVisualizer(g, title=title)
    docs_path = os.path.join(specific_output_path, "docs")
    docs.build(docs_path)  # => build and save docs/visualization.

    viz = Dataviz(g, title=title)
    viz_path = os.path.join(specific_output_path, "dendro")
    viz.build(viz_path)  # => build and save docs/visualization.
    logger.info("-> built ontospy documentation for %s", turtle_file)


# ===== docs command =====


def docs(args):
    logger.debug("Docs subcommand started!")

    files = [args.VOCAB] if args.VOCAB.is_file() else [*Path(args.VOCAB).iterdir()]
    turtle_files = [f for f in files if f.suffix.lower() in (".turtle", ".ttl")]

    if not turtle_files:
        logger.info("-> Nothing to do. No turtle file(s) found.")
        return

    for file in turtle_files:
        logger.debug('Processing "%s"', file)
        outdir = file.parent if args.outdir is None else args.outdir
        if any(outdir.iterdir()) and not args.force:
            logger.warning(
                'The folder "%s" is not empty. Use "--force" to write to the folder anyway.',
                outdir,
            )
            return

        if args.style == "pylode":
            run_pylode(file, outdir)
            # generate index.html linking all tagged version in CI
            if os.getenv("CI") is not None:
                voc_path = Path(".")
                build_multirelease_index(voc_path, outdir)

        elif args.style == "ontospy":
            run_ontospy(file, outdir)
        else:  # pragma: no cover
            # This should not be reached since argparse checks --style choices.
            msg = f"Unsupported style: {args.style}"
            raise AssertionError(msg)
