This is the repository for working in NFDI4Cat on **Vocabularies for analytics, synthesis and heterogeneous catalysis**.

Additional files and information can be found in the HLRS cloud:

 * [Folder of TA1 subgroup Analytics-Synthesis-HeterogeneousCatalysis](https://edocs.hlrs.de/nextcloud/apps/files/?dir=/NFDI4Cat/Project-related%20activities/Task%20Areas/TA1/Subgroup_Analytics-Synthesis-HeterogCatalysis&fileid=155479)
 * [Top level folder for TA1](https://edocs.hlrs.de/nextcloud/apps/files/?dir=/NFDI4Cat/Project-related%20activities/Task%20Areas/TA1&fileid=96729)

# Wrapper script for VocExcel

## Installation

The installation requires internet access since we install VocExcel directly from github.

Preconditions:
 * git
 * Python (3.8 or newer)
   - The instructions below assume that the [launcher](https://docs.python.org/3.10/using/windows.html#python-launcher-for-windows) is also installed. The launcher is included by default in Windows installers from [python.org](https://www.python.org/downloads/)
  
## Installation steps:

Checkout this repository

`git clone https://gitlab.fokus.fraunhofer.de/nfdi4cat/ta1-ontologies/heterogen-synth.git`

Enter the checked out directory

`cd heterogen-synth`
 
Create a virtual environment in a local subfolder ".venv" (Note that the command is for windows. Replace "py" with "python3" on other platforms.):

`py -m venv .venv`

Activate the virtual environment (This is again for windows).

`.venv\scripts\activate.bat` (cmd) or `.venv\scripts\Activate.ps1` (powershell)

Update the packages in the virtual environment.

`py -m pip install -U pip setuptools`

Install dependencies.

`pip install -r requirements.txt`


## Typical use

Run the wrapper and show the help message.

`py vocexcel_4cat.py --help`

To create a new vocabulary use the NFDI4Cat-adjusted template from the subfolder `templates` subfolder. Typically, when a new vocabulary is created you want to create IRIs from the preferred labels:

`py vocexcel_4cat.py -i vocabulary.xlsx`

This will fill the IRI-column for all rows with missig IRI entries.

Manually filling the Children URI (in sheet "Concepts") and Members URI (in sheet "Collections") with URIs can be tedious. Alternatively, the additional columns "Children by Pref. Label" and "Members by Pref. Label" allow to specify the children or members by their preferred label. Then the script can be used to fill the URI columns:

`py vocexcel_4cat.py -r vocabulary.xlsx`

Finally, the vocabulary file can be converted to turtle format. In this case the wrapper script passes the job on to vocexcel:

`py vocexcel_4cat.py vocabulary.xlsx`

A turtle file `vocabulary.ttl` is created in the same directory a where the xlsx-file is located.

## Contribute your vocabulary

To contribute your vocabulary to this repository create a merge request that adds your Excel-file to the folder `inbox-excel-vocabs`.
