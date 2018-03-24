import os

from . import bib_utils as bu


def build_database_from_folder(root_folder):
    root_folder = os.path.abspath(root_folder)
    bibdat = bu.BetterBibDatabase()
    for root, _, files in os.walk(root_folder):
        for f in files:
            _, ext = os.path.splitext(f)
            if ext != '.pdf':
                continue
            try:
                bibdat.add_entry_by_file(os.path.join(root, f))
            except (bu.DoiNotFoundError, bu.BibRetrievalError, bu.PdfParsingError) as err:
                print(err.args[0])

    return bibdat