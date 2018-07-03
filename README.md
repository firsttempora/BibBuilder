# BibBuilder
Python package containing utilities to manuipulate BibTex .bib files.

## Quick install
1. Clone the repository
1. Make sure you have `pip` v10 or greater, either as your system `pip` or in the virtual environment you will install to
(lower versions _may_ work but will give error messages about being unable to build wheels)
1. In the package directory (the one with `setup.py`) run `pip install --user .`. If installing to a virtual environment, 
omit the `--user` flag.
1. The programs `bb-build`, `bb-web`, and `bb-merge` will be placed in the standard binary (`bin`) directory for how you ran `pip`.
1. Add the installation directory to your `PATH` environmental variable, or link the `bb-` programs to a directory that is on your
`PATH`.

This has been tested with Python 3.5. 

## Command line programs available
### bb-build

The `bb-build` program is designed to walk a directory containing PDFs of journal articles, extract their DOIs, and retrieve a 
BibTex entry for each paper, assembling them into a new .bib file. It is also designed to update a .bib file, meaning:

* It has the option to skip papers in the folder if an entry with the same DOI already exists
* It can store the options used in the .bib file, so that the next update uses the same options

### bb-web

The `bb-web` program is designed to create an HTML file from a .bib file for use on a website. The assumption is that you
would have a .bib file containing all publications and/or presentations that you want to include on a website.
It has options to:

* Bold one or more authors
* Put papers with a bolder author as first author near the top of each year
* Extract only entries of specific types in the .bib file

### bb-merge

The `bb-merge` program is designed to combine two or more .bib files. It will avoid duplicating identical entries, and by
default will ask what to do if it finds two entries that share a key. It also has the option to exclude entries that are identified
by a key that exists in one or more "exclude" .bib files - this way you can ensure that the merged .bib file will be compatible 
as an additional bib resource alongside one or more other .bib files.
