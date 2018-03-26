import argparse
from datetime import datetime
import logging
import os

from . import bib_utils as bu, root_logger

# TODO: implement pruning
# TODO: continue to add doi regex to get as many papers as possible
# TODO: fix --quiet


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
                root_logger.warning(err.args[0])

    return bibdat


def arg_or_env_var(arg, env_var_name, default_val=None):
    if arg is not None:
        return arg




def arg_or_env_var(arg, env_var_name, bib_file=None, default_val=None, is_path=False, parsing_fxn=str):
    # When getting the top directory, prefer:
    #   First, the command line argument (passed in)
    #   Second, a directory given at the top of the file
    #   Third, an environmental variable
    #   Fourth, the current directory

    if arg is not None:
        return arg

    if bib_file is not None and os.path.isfile(bib_file):
        # Try to find it in the bib file itself
        with open(bib_file, 'r') as bib_obj:
            for line in bib_obj:
                if line.startswith('%{}'.format(env_var_name)):
                    _, arg = line.split('=')
                    arg = parsing_fxn(arg.strip())
                    if isinstance(arg, str) and len(arg) > 0 and is_path:
                        arg = bu.change_home_dir(arg, os.getenv('HOME'))
                    return arg

    return parsing_fxn(os.getenv(env_var_name, default_val))


def setup_logging(verbosity, bibfile, no_log_file):
    if verbosity <= 0:
        root_logger.setLevel(logging.WARNING)
    elif verbosity == 1:
        root_logger.setLevel(logging.INFO)
    elif verbosity >= 2:
        root_logger.setLevel(logging.DEBUG)

    if verbosity < 0:
        # If told to be quiet, remove the stream handler rather than setting the level so that the log file at least
        # gets warnings and above - this is intended so that output to the console can be suppressed while the log file
        # gets a list of files that failed parsing.
        root_logger.removeHandler(root_logger.handlers[0])

    if not no_log_file:
        log_file_name, _ = os.path.splitext(bibfile)
        log_file_name += '.log'
        log_file_handler = logging.FileHandler(log_file_name, mode='a')
        root_logger.addHandler(log_file_handler)
        # Go ahead and log the current date/time
        msg = '# BibBuilder: operating on {} at {} #'.format(os.path.basename(bibfile), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        banner = '#'*len(msg)
        root_logger.critical('\n{0}\n{1}\n{0}\n'.format(banner, msg))


def parse_args():
    parser = argparse.ArgumentParser(description='Utility to build or update a BibTex file from PDF files')
    parser.add_argument('bibtex_file', default=None, help='The BibTex file to output or, if exists, update. If not given, can be specified as the environmental variable BIBBUILDER_BIB_FILE')
    parser.add_argument('--pdf-top-dir', help='The top directory to search for PDF files in. If not given, uses current or the environmental variable BIBBUILDER_PDF_DIR')
    parser.add_argument('--prune', action='store_true', help='Remove entries who do not have a corresponding file')
    parser.add_argument('--no-backup', action='store_true', help='Do not make a backup of the .bib file before modifying it')
    # Need to use 'store_const' here so that the default is None; it will be set to False if necessary by arg_or_env_var
    parser.add_argument('--no-duplicates', action='store_const', const=True, help='Do not include files if a duplicate DOI already exists')
    parser.add_argument('-u', '--update-home-dir', action='store_true', help='Just update the home directory in the "file" field of each entry; do nothing else')

    parser.add_argument('--no-log-file', action='store_true', help='Do not create an automatic log file')

    parser.add_argument('--working-dir', help='Set the working directory')

    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-v', '--verbose', default=0, action='count', help='Increase logging to console')
    log_group.add_argument('-q', '--quiet', action='store_true', help='Suppress logging to console')

    args = parser.parse_args()

    if args.working_dir is not None:
        os.chdir(args.working_dir)

    bib_file = arg_or_env_var(args.bibtex_file, 'BIBBUILDER_BIB_FILE')
    if bib_file is None:
        bu.shell_error('Positional argument BIBTEXT_FILE must be given or the env. variable BIBBUILDER_BIB_FILE must be set')

    pdf_top_dir = arg_or_env_var(args.pdf_top_dir, 'BIBBUILDER_PDF_DIR', bib_file, is_path=True, default_val='.')
    do_prune = args.prune
    do_not_backup = args.no_backup
    no_duplicates = arg_or_env_var(args.no_duplicates, 'BIBBUILDER_NO_DUP', bib_file, default_val=False, parsing_fxn=lambda x: x=='True')
    update_home_dir = args.update_home_dir

    if args.quiet:
        verbosity = -1
    else:
        verbosity = args.verbose

    setup_logging(verbosity, bib_file, args.no_log_file)

    return bib_file, pdf_top_dir, do_prune, do_not_backup, no_duplicates, update_home_dir


def main():
    bib_file, pdf_top_dir, do_prune, do_not_backup, no_duplicates, update_home_dir_only = parse_args()
    bib_dat = bu.init_bib_database(bib_file, no_backup=do_not_backup)
    if update_home_dir_only:
        pass
    else:
        bib_dat = update_database_from_folder(bib_dat, pdf_top_dir, no_duplicates=no_duplicates)
    bib_dat.save_to_file(bib_file, BIBBUILDER_PDF_DIR=pdf_top_dir, BIBBUILDER_NO_DUP=no_duplicates)

if __name__ == '__main__':
    main()
