import argparse
import os

from . import bib_utils as bu

# TODO: implement pruning
# TODO: implement logging better, especially a list of files that failed
# TODO: continue to add doi regex to get as many papers as possible


def update_database_from_folder(bibdat, root_folder, no_duplicates=False):
    root_folder = os.path.abspath(root_folder)
    for root, _, files in os.walk(root_folder):
        for f in files:
            _, ext = os.path.splitext(f)
            if ext != '.pdf':
                continue
            try:
                bibdat.add_entry_by_file(os.path.join(root, f), skip_if_doi_exists=no_duplicates)
            except (bu.DoiNotFoundError, bu.BibRetrievalError, bu.PdfParsingError) as err:
                print(err.args[0])

    return bibdat


def arg_or_env_var(arg, env_var_name, default_val=None):
    if arg is not None:
        return arg

    return os.getenv(env_var_name, default_val)


def parse_args():
    parser = argparse.ArgumentParser(description='Utility to build or update a BibTex file from PDF files')
    parser.add_argument('bibtex_file', default=None, help='The BibTex file to output or, if exists, update. If not given, can be specified as the environmental variable BIBBUILDER_BIB_FILE')
    parser.add_argument('--pdf-top-dir', help='The top directory to search for PDF files in. If not given, uses current or the environmental variable BIBBUILDER_PDF_DIR')
    parser.add_argument('--prune', action='store_true', help='Remove entries who do not have a corresponding file')
    parser.add_argument('--no-backup', action='store_true', help='Do not make a backup of the .bib file before modifying it')
    parser.add_argument('--no-duplicates', action='store_true', help='Do not include files if a duplicate DOI already exists')
    parser.add_argument('-u', '--update-home-dir', action='store_true', help='Just update the home directory in the "file" field of each entry; do nothing else')

    args = parser.parse_args()

    bib_file = arg_or_env_var(args.bibtex_file, 'BIBBUILDER_BIB_FILE')
    if bib_file is None:
        bu.shell_error('Positional argument BIBTEXT_FILE must be given or the env. variable BIBBUILDER_BIB_FILE must be set')

    pdf_top_dir = arg_or_env_var(args.pdf_top_dir, 'BIBBUILDER_PDF_DIR', default_val='.')
    do_prune = args.prune
    do_not_backup = args.no_backup
    no_duplicates = args.no_duplicates
    update_home_dir = args.update_home_dir

    return bib_file, pdf_top_dir, do_prune, do_not_backup, no_duplicates, update_home_dir


def main():
    bib_file, pdf_top_dir, do_prune, do_not_backup, no_duplicates, update_home_dir_only = parse_args()
    bib_dat = bu.init_bib_database(bib_file, no_backup=do_not_backup)
    if update_home_dir_only:
        pass
    else:
        bib_dat = update_database_from_folder(bib_dat, pdf_top_dir, no_duplicates=no_duplicates)
    bib_dat.save_to_file(bib_file)

if __name__ == '__main__':
    main()