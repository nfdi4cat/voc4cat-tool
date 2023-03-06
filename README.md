# SKOS vocabulary creation & maintenance with GitHub & Excel

**[voc4cat](https://github.com/nfdi4cat/voc4cat-playground)** is a vocabulary for catalysis developed in NFDI4Cat.

Related to voc4cat we developed a **toolbox for collaboratively maintaining SKOS vocabularies on github using Excel** (xlsx) as user-friendly interface. It consists of several parts:

- **voc4cat-tool** (this repository)
  - A commandline tool that adds additional options to [vocexcel](https://github.com/RDFLib/VocExcel) without changing or copying any code from the original vocexcel project.
- **[voc4cat-template](https://github.com/nfdi4cat/voc4cat-template)**
  - A github project template for managing SKOS-vocabularies using a GitHub-based workflows including automation by gh-actions.
- **[voc4cat-playground](https://github.com/nfdi4cat/voc4cat-playground)**
  - A testbed for playing with the voc4cat workflow. The playground is a test-deployment of the voc4cat-template.

## Basics

TODO - explain dir structure and general principles.

All vocabularies that have gone through the standard contribution process of

- submission of merge request,
- review of merge request,
- approval of merge request

finally land in the folder `vocabularies`.

## New vocabularies

Please use the Excel file from the template folder to create vocabularies that are compatible with this repository.
If you already have a turtle file, you may convert it with voc4cat to xlsx (Excel).
Be careful that you use a different name for your vocabulary then the ones already present in the `vocabularies` folder.

The rest of the process is the same as in "Update existing vocabularies" below.

## Update existing vocabularies

To add or change details in an existing vocabulary, submit a pull request with an updated Excel-file that has the same name as the vocabulary that you want to update
(see `vocabularies` folder for the names of existing vocabularies).
If you don't have an Excel file but just the turtle file, you can use voc4cat (see below) to convert the turtle file to xlsx (Excel).

Upon submission of the merge request, the Excel file is automatically processed by a CI pipeline.
The results (updated Excel-file, documentation, dendogram, processing log) will be available after about 1 min as download on the merge request page (as so called "artifact").
If you need to fix something just update the merge request branch. This will trigger the pipeline to run again.

Please describe your changes and the motivation for the changes in the merge request note(s) or link to an issue with this information. This will help reviewers to decide on the proposed change.

Finally, when the proposed merge request is accepted, your changes will be integrated in the vocabularies in the folder `vocabularies`.

# Tool voc4cat

To support what is not provided by the original vocexcel project we have developed this wrapper "voc4cat" that augments vocexcel with additional options like

- Checking our NFDI4Cat-Excel template
- Enriching our NFDI4Cat-Excel template (e.g. add IRIs)
- Processing all files in a folder at once
- Generating documentation (with [ontospy](http://lambdamusic.github.io/Ontospy/))
- Support for expressing concept-hierarchies by indentation.


## Installation

The installation requires internet access since we install vocexcel directly from GitHub.

Preconditions:

- git
- Python (3.8 or newer)

voc4cat works on windows, linux and mac. However, the command examples below assume that you work on windows
and that the [launcher](https://docs.python.org/3.11/using/windows.html#python-launcher-for-windows) is also installed.
The launcher is included by default in Windows installers from [python.org](https://www.python.org/downloads/). 
If you don't have the launcher replace `py` by `python` (or `python3`, depending on your OS) in the command below.

## Installation steps

Checkout this repository

`git clone https://github.com/nfdi4cat/voc4cat-tool.git`

Enter the directory to which you cloned.

`cd voc4cat-tool`

Create a virtual environment in a local subfolder ".venv" (Note that the command is for windows. Replace "py" with "python3" on other platforms.):

`py -m venv .venv`

Activate the virtual environment (This is again for windows).

`.venv\scripts\activate.bat` (cmd) or `.venv\scripts\Activate.ps1` (powershell)

Update the packages in the virtual environment.

`py -m pip install -U pip`

Install voc4cat into the virtual environment.

`pip install .`

## Typical use

Run the voc4at and show the help message.

`voc4cat --help`

To create a new vocabulary use the voc4Cat-adjusted template from the `templates` subfolder.
Typically, when a new vocabulary is created you want to create IRIs from the preferred labels:

TODO update for make-iris!

`voc4cat -i Your_Vocabulary.xlsx`

This will fill the IRI-column for all rows with missing IRI entries.

Manually filling the Children URI (in sheet "Concepts") and Members URI (in sheet "Collections") with URIs can be tedious.
An easier way to express hierarchies between concepts, is to use indentation. voc4Cat supports Excel-indentation (default).
voc4cat can also convert other indentations (e.g. by 3 spaces per level) into Excel-indentation.
voc4cat supports converting between indentation-based hierarchy and Children-URI hierarchy (both directions). For example, use

`voc4cat --hierarchy-from-indent --output_directory output example/indent_043_4Cat.xlsx`

or if you were using 3 spaces per level

`voc4cat --hierarchy-from-indent --indent-separator "   " --output_directory output example/indent_3spaces_043_4Cat.xlsx`

to convert to ChildrenURI-hierarchy. For ChildrenURI-hierarchy to Excel-indentation, use

`voc4cat --hierarchy-to-indent --output_directory output example/concept_hierarchy_043_4Cat.xlsx`

Finally, the vocabulary file can be converted to turtle format. In this case the wrapper script passes the job on to vocexcel:

`voc4cat vocabulary.xlsx`

A turtle file `vocabulary.ttl` is created in the same directory where the xlsx-file is located.

It is also possible to create an xlsx file from a turtle file. Optionally a custom template can be specified:

`voc4cat --template template/VocExcel-template_043_4Cat.xlsx vocabulary.ttl`

Options that are specific for vocexcel can be put at the end of a `voc4cat` command.
Here is an example that forwards the `-e 3` and `-m 3` options to vocexcel and moreover demonstrates a complex combination of options (as used in CI):

`voc4cat --check --forward --docs --output_directory outbox inbox-excel-vocabs/ -e 3 -m 3`

## Feedback and code contributions

Just create an issue here. We appreciate any kind of feedback and reasoned criticism.

If you want to contribute code, that is even better! We suggest to create an issue first to get early feedback on your plans before you spent too much time.

By contributing you agree that your contributions fall under the project´s MIT license.

## Acknowledgement

This work was funded by the German Research Foundation (DFG) through the project "[NFDI4Cat](https://www.nfdi4cat.org) - NFDI for Catalysis-Related Sciences" (DFG project no. [441926934](https://gepris.dfg.de/gepris/projekt/441926934)), within the National Research Data Infrastructure ([NFDI](https://www.nfdi.de)) programme of the Joint Science Conference (GWK).
