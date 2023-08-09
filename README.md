# SKOS vocabulary management with GitHub & Excel

## Overview

**[voc4cat](https://github.com/nfdi4cat/voc4cat)** is the vocabulary for catalysis developed in NFDI4Cat.

For voc4cat we developed a **toolbox for collaboratively maintaining SKOS vocabularies on GitHub using Excel** (xlsx-files) as user-friendly interface. It consists of several parts:

- **voc4cat-tool** (this repository)
  - A command-line tool to convert vocabularies from Excel to SKOS (turtle/rdf) and validate the vocabulary. Validation includes formal validation with SHACL-profiles but also additional checks. The `voc4cat` tool can be run locally but is also well suited for integration in CI-pipelines. It was inspired by [RDFlib/VocExcel](https://github.com/nfdi4cat/VocExcel). Parts of the vocexcel code base were merged into this repository (see git history).
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)**
  - A github project template for managing SKOS-vocabularies using a GitHub-based workflows including automation by gh-actions.
- **[voc4cat-playground](https://github.com/nfdi4cat/voc4cat-playground)**
  - A testbed for playing with the voc4cat workflow. The playground is a test-deployment of the voc4cat-template.
- **[voc4cat](https://github.com/nfdi4cat/voc4cat)**
  - A SKOS vocabulary for the catalysis disciplines that uses the voc4cat workflow for real work.

## Command-line tool voc4cat

voc4cat was mainly developed to be used in gh-actions but it is also useful as a locally installed command line tool. It has the following features.

- Convert between SKOS-vocabularies in Excel/xlsx format and rdf-format (turtle) in both directions.
- Check/validate SKOS-vocabularies in rdf/turtle format with the [vocpub](https://w3id.org/profile/vocpub) SHACL-profile.
- Use a vocabulary-configuration file to specify for example ID ranges for each contributor.
- Check xlsx vocabulary files for errors or incorrect use of IDs (voc4cat uses pydantic for this validation)
- Generate documentation from SKOS/turtle vocabulary file using [pyLODE](https://github.com/RDFLib/pyLODE) (or [ontospy](http://lambdamusic.github.io/Ontospy/))
- Express concept-hierarchies in xlsx by indentation.
- Consistently update all IRIs in the xlsx vocabulary (e.g. with new namespace or IDs)

voc4cat works on files or folders. If a folder is given all matching files are processed at once.

### Installation requirements

To start you need:

- git
- Python (3.10 or newer)

voc4cat works on windows, linux and mac. However, the examples below assume that you work on windows
and that the [launcher](https://docs.python.org/3.11/using/windows.html#python-launcher-for-windows) is installed.
The launcher is included by default in Windows installers from [python.org](https://www.python.org/downloads/).
If you don't have the launcher replace `py` by `python` (or `python3`, depending on your OS) in the commands below.

### Installation steps

Checkout this repository

`git clone https://github.com/nfdi4cat/voc4cat-tool.git`

Enter the directory to which you cloned.

`cd voc4cat-tool`

Create a virtual environment in a local subfolder ".venv" (This command is for windows. Replace "py" with "python3" on other platforms.):

`py -m venv .venv`

Activate the virtual environment (This is again for windows).

`.venv\scripts\activate.bat` (cmd) or `.venv\scripts\Activate.ps1` (powershell)

Update pip in the virtual environment.

`py -m pip install -U pip`

Install voc4cat into the virtual environment.

`pip install .`

To install including all development tools use `pip install .[dev]` for just the test tools us `pip install .[tests]`. For tests we use [pytest](https://docs.pytest.org).

### Typical use

The available commands and options can be explored via the help system:

`voc4cat --help` (or simply `voc4cat`)

which lists all available sub commands. These have their own help, for example:

`voc4cat transform --help`

To create a new vocabulary use the voc4cat-adjusted template from the `templates` subfolder.
For starting you can use simple temporary IRIs like (`ex:my_term`) for your concepts.
With voc4cat you can later replace these later by different namespaces and/or different numeric IDs.

For expressing hierarchies in SKOS ("broader"/"narrower") voc4cat offers two options. One way is to enter a list of children IRIs  (in sheet "Concepts"). However, filling the Children URI columns with lists of IRIs can be tedious. Therefore, voc4cat offers a second easier way to express hierarchies between concepts and that is by indentation. voc4Cat understands Excel-indentation (the default) but can also work with other indentation formats (e.g. 3 spaces per level). To switch between the two representations, use the `transform` sub-command. For example, use

`voc4cat transform --from-indent --outdir outbox example/photocatalysis_example_indented_prelim-IDs.xlsx`

or if you were using 3 spaces per level (This file does not yet exist.)

`voc4cat transform --from-indent --indent "   " --inplace outbox outbox\photocatalysis_example_prelim-IDs.xlsx`

to convert to ChildrenURI-hierarchy. To create such a file convert for example from ChildrenURI-hierarchy to indentation by

`voc4cat transform --to-indent --indent "   " --outdir outbox example/photocatalysis_example_prelim-IDs.xlsx`

As mentioned above, you can replace all IDs belonging to a given prefix (here `temp`) by numeric IDs e.g. starting from 1001:

`voc4cat transform --make-ids temp 1001 --outdir outbox example/photocatalysis_example_prelim-IDs.xlsx`

This will consistently update all IRIs matching the `temp:`-prefix in the sheets "Concepts", "Additional Concept Features" and "Collections".

Finally, the vocabulary file can be converted from xlsx to SKOS/turtle format.

`voc4cat convert example/photocatalysis_example.xlsx`

A turtle file `photocatalysis_example.ttl` is created in the same directory where the xlsx-file is located.

The reverse is also possible. You can create an xlsx file from a turtle vocabulary file.
Optionally a custom XLSX-template-file can be specified for this conversion:

`voc4cat convert -O outbox --template templates/voc4cat_template_043.xlsx example/photocatalysis_example.ttl`

In addition to `transform` and `convert` voc4cat offers checking and validation under the sub-command `check` and documentation generation under `docs`.
See the command line help for details.

## Feedback and code contributions

Please create an issue here. We highly appreciate your feedback.

If you plan to contribute code, we suggest to create an issue first to get early feedback on your ideas before you spend too much time.

By contributing you agree that your contributions fall under the project´s BSD-3-Clause [license](LICENSE).

## Acknowledgement

This work was funded by the German Research Foundation (DFG) through the project "[NFDI4Cat](https://www.nfdi4cat.org) - NFDI for Catalysis-Related Sciences" (DFG project no. [441926934](https://gepris.dfg.de/gepris/projekt/441926934)), within the National Research Data Infrastructure ([NFDI](https://www.nfdi.de)) programme of the Joint Science Conference (GWK).
