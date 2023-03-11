# SKOS vocabulary creation & maintenance with GitHub & Excel

## Overview

**[voc4cat](https://github.com/nfdi4cat/voc4cat)** is the vocabulary for catalysis developed in NFDI4Cat.

Related to voc4cat we developed a **toolbox for collaboratively maintaining SKOS vocabularies on github using Excel** (xlsx) as user-friendly interface. It consists of several parts:

- **voc4cat-tool** (this repository)
  - A commandline tool that adds additional options to [vocexcel](https://github.com/nfdi4cat/VocExcel) without changing or copying any code from the original vocexcel project (GPL 3 licensed).
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)**
  - A github project template for managing SKOS-vocabularies using a GitHub-based workflows including automation by gh-actions.
- **[voc4cat-playground](https://github.com/nfdi4cat/voc4cat-playground)**
  - A testbed for playing with the voc4cat workflow. The playground is a test-deployment of the voc4cat-template.


## Commandline tool voc4cat

To support what is not provided by the original vocexcel project we have developed this wrapper "voc4cat" that augments vocexcel with additional options like

- Checking our NFDI4Cat-Excel template
- Enriching our NFDI4Cat-Excel template (e.g. add IRIs)
- Processing all files in a folder at once
- Generating documentation (with [ontospy](http://lambdamusic.github.io/Ontospy/))
- Support for expressing concept-hierarchies by indentation.

Since mid 2022 voc4cat should be used with our vocexcel fork [nfdi4cat/vocexcel](https://github.com/nfdi4cat/vocexcel). The original project (now at [RDFlib/vocexcel](https://github.com/RDFLib/VocExcel)) changed its templates substantially which made it too cumbersome to keep our code and the customized templates compatible.

## Installation

The installation requires internet access since we install vocexcel directly from GitHub.

Preconditions:

- git
- Python (3.8 or newer)

voc4cat works on windows, linux and mac. However, the command examples below assume that you work on windows
and that the [launcher](https://docs.python.org/3.11/using/windows.html#python-launcher-for-windows) is also installed.
The launcher is included by default in Windows installers from [python.org](https://www.python.org/downloads/). 
If you don't have the launcher replace `py` by `python` (or `python3`, depending on your OS) in the commands below.

## Installation steps

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


## Typical use

Show a help message for the voc4cat command line tool with all available options.

`voc4cat --help` (or simply `voc4cat`)

To create a new vocabulary use the voc4Cat-adjusted template from the `templates` subfolder.
You may first use simple temporary IRIs like (`new:my_term`). These temporary IRIS may be text based. 

With voc4cat you can later replace all IDs belonging to a given prefix (here `ex`) by numeric IDs e.g. starting from 1001:

`voc4cat --make-ids ex 1001 --output-directory output example/concept_hierarchy_043_4Cat.xlsx`

This will update all IRIs matching the `ex:`-prefix in the sheets "Concepts", "Additional Concept Features" and "Collections".

Manually filling the Children URI (in sheet "Concepts") and Members URI (in sheet "Collections") with lists of IRIs can be tedious.
An easier way to express hierarchies between concepts is to use indentation.
voc4Cat understands Excel-indentation (the default) for this purpose but can also work with other indentation formats (e.g. by 3 spaces per level).
voc4cat supports converting between indentation-based hierarchy and Children-URI hierarchy (both directions). For example, use

`voc4cat --hierarchy-from-indent --output-directory output example/indent_043_4Cat.xlsx`

or if you were using 3 spaces per level

`voc4cat --hierarchy-from-indent --indent-separator "   " --output-directory output example/indent_3spaces_043_4Cat.xlsx`

to convert to ChildrenURI-hierarchy. For ChildrenURI-hierarchy to Excel-indentation, use

`voc4cat --hierarchy-to-indent --output-directory output example/concept_hierarchy_043_4Cat.xlsx`

Finally, the vocabulary file can be converted to turtle format. In this case the wrapper script passes the job on to vocexcel:

`voc4cat vocabulary.xlsx`

A turtle file `vocabulary.ttl` is created in the same directory where the xlsx-file is located.

It is also possible to create an xlsx file from a turtle file. Optionally a custom template can be specified:

`voc4cat --template template/VocExcel-template_043_4Cat.xlsx vocabulary.ttl`

Options that are specific for vocexcel can be put at the end of a `voc4cat` command.
Here is an example that forwards the `-e 3` and `-m 3` options to vocexcel and moreover demonstrates a complex combination of options (as used in CI):

`voc4cat --check --forward --docs --output-directory outbox inbox-excel-vocabs/ -e 3 -m 3`

## Feedback and code contributions

Just create an issue here. We appreciate any kind of feedback and reasoned criticism.

If you want to contribute code, we suggest to create an issue first to get early feedback on your plans before you spent too much time.

By contributing you agree that your contributions fall under the project´s MIT license.

## Acknowledgement

This work was funded by the German Research Foundation (DFG) through the project "[NFDI4Cat](https://www.nfdi4cat.org) - NFDI for Catalysis-Related Sciences" (DFG project no. [441926934](https://gepris.dfg.de/gepris/projekt/441926934)), within the National Research Data Infrastructure ([NFDI](https://www.nfdi.de)) programme of the Joint Science Conference (GWK).
