This is the repository for working in NFDI4Cat on **Vocabularies analytics, synthesis and heterogeneous catalysis**.

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

Run the wrapper and show, for example, the help message.

`py vocexcel_4cat.py --help`
