from __future__ import print_function, absolute_import, division

import argparse
import os
import sys
from textui import uielements as uiel

from .. import bib_utils as bu

_default_merged_file = 'merged.bib'


# Functions to resolve conflicts
def _are_entries_equivalent(entry1, entry2):
    # In the future, this could be updated to use fuzzier logic
    return entry1 == entry2


def _change_entry_key(entry, all_other_keys):
    new_key = uiel.user_input_value('Enter a new key', testfxn=lambda k: k not in all_other_keys,
                                    testmsg='That key already exists. Please enter another.',
                                    emptycancel=False)
    entry['ID'] = new_key
    return entry


def _conflict_resolve_ask_user(bib_dat, new_bib_dat, conflicting_key):
    print('\nConflicting key, "{key}" in files {file1} and {file2}.'.format(key=conflicting_key,
                                                                            file1=bib_dat.filename,
                                                                            file2=new_bib_dat.filename))
    print('\nEntry for "{key}" in {file}'.format(key=conflicting_key, file=bib_dat.filename))
    print(bib_dat.get_entry_as_string(conflicting_key))
    print('\nEntry for "{key}" in {file}'.format(key=conflicting_key, file=new_bib_dat.filename))
    print(new_bib_dat.get_entry_as_string(conflicting_key))

    file_ind = uiel.user_input_list('What action to take?',
                                    ['Keep entry from {}'.format(bib_dat.filename),
                                     'Keep entry from {}'.format(new_bib_dat.filename),
                                     'Keep both but change the second key',
                                     'Abort'],
                                    returntype='index',
                                    emptycancel=False,
                                    printcols=False)

    if file_ind == 0:
        # Keeping the entry in the current base bib_dat, nothing to do
        return
    elif file_ind == 1:
        # Remove the original entry in the Bib database and add in the new one
        bib_dat.replace_entry_by_key(conflicting_key, new_bib_dat[conflicting_key])
    elif file_ind == 2:
        new_entry = _change_entry_key(new_bib_dat[conflicting_key], bib_dat.ids + new_bib_dat.ids)
        bib_dat.add_entry(new_entry)
    elif file_ind == 3:
        sys.exit(2)


def _conflict_resolve_first(bib_dat, new_bib_dat, conflicting_key):
    # Nothing needs done because we are keeping the first bib dat unmodified
    pass


def _conflict_resolve_last(bib_dat, new_bib_dat, conflicting_key):
    bib_dat.replace_entry_by_key(conflicting_key, new_bib_dat[conflicting_key])


def _conflict_resolve_error(bib_dat, new_bib_dat, conflicting_key):
    print('Duplicate key ({key}) in {file1} and {file2}, aborting as requested'.format(key=conflicting_key, file1=bib_dat.filename, file2=new_bib_dat.filename),
          file=sys.stderr)
    sys.exit(1)

_conflict_resolution_fxns = {'ask': _conflict_resolve_ask_user,
                             'first': _conflict_resolve_first,
                             'last': _conflict_resolve_last,
                             'error': _conflict_resolve_error}


def merge_bib_files(base_bib_dat, extra_bib_files, excluded_keys, exclude_interactive=False, conflict_behavior='ask', verbose=0):
    for bib_file in extra_bib_files:
        new_bib_dat = bu.init_bib_database(bib_file, no_backup=True, update_home=False)
        # We could just use the dict.update() method, but we want more control over how to handle conflicts
        for key in new_bib_dat.entries_dict.keys():
            if key not in base_bib_dat.entries_dict:
                # We DO want to append keys that will be excluded so that the user gets a message when
                # they are removed
                base_bib_dat.entries.append(new_bib_dat[key])
            elif not _are_entries_equivalent(base_bib_dat[key], new_bib_dat[key]):
                if key not in excluded_keys or exclude_interactive:
                    # However, we DON'T want to pester the user to deal with a duplicated key if it is just going to
                    # be removed. So if the duplicate key is to be removed automatically anyway, don't bother adding it.
                    # But, if we're going to give the user a chance to enter a different key for the key to be removed,
                    # then we should also give them the chance to determine which key that is.
                    _conflict_resolution_fxns[conflict_behavior](base_bib_dat, new_bib_dat, key)


def list_excluded_keys(exclude):
    excluded_keys = dict()
    for exclude_file in exclude:
        exclude_dat = bu.init_bib_database(exclude_file, no_backup=True, update_home=False)
        # Create the full list so that if the user chooses to rename the conflicting key we can
        # ensure the new key doesn't exist in any of the exclude files
        excluded_keys.update({k: exclude_file for k in exclude_dat.ids})

    return excluded_keys


def remove_excluded_bib_keys(base_bib, excluded_keys, ask_to_remove=False, verbose=0):
    for key in base_bib.ids:
        if key in excluded_keys:
            if not ask_to_remove:
                base_bib.remove_entry_by_key(key)
            else:
                print('Entry with key "{key}" is in one of the exclude files ({exfile})'.format(
                    key=key, exfile=excluded_keys[key]
                ))
                print(base_bib.get_entry_as_string(key))
                action = uiel.user_input_list('\nWhat action to take?', ['Remove entry', 'Change entry key'],
                                              emptycancel=False, returntype='index', printcols=False)
                if action == 0:
                    if verbose > -1:
                        print('Removing entry "{}"'.format(key))
                    base_bib.remove_entry_by_key(key)
                elif action == 1:
                    # This should operate in-place
                    _change_entry_key(base_bib[key], [k for k in excluded_keys] + base_bib.ids)
                else:
                    raise NotImplementedError('No method has been implemented for that action')


def parse_args(argstring=None):
    parser = argparse.ArgumentParser(description='Merge two or more BibTex .bib files together')
    parser.add_argument('bib_files', nargs='+', help='The .bib files to merge')
    parser.add_argument('-o', '--output-file', default='merged.bib', help='The name to give the merged file. '
                                                                          'Default is %(default)s.')
    parser.add_argument('-e', '--exclude', action='append', default=[], help='A .bib file whose entries should be '
                                                                             'excluded from the merged file. That is, '
                                                                             'any entries in one of the files to be '
                                                                             'merged that share a key with an entry in '
                                                                             'this file will not be included in the '
                                                                             'merged .bib file. This is helpful to '
                                                                             'avoid duplicate keys. This option may be '
                                                                             'specified multiple times.')
    parser.add_argument('-x', '--conflict-mode', choices=_conflict_resolution_fxns.keys(), default='ask',
                        help='How to resolve conflicting keys. '
                             '"ask" = always ask, '
                             '"first" = use first instance of that key, '
                             '"last" = use last instance of that key, '
                             '"error" = exit with error code 1')
    parser.add_argument('-i', '--interactive-remove', action='store_true', help='Ask before removing keys listed in '
                                                                                '--exclude files')
    clobber_group = parser.add_mutually_exclusive_group()
    clobber_group.add_argument('-c', '--clobber', action='store_true',
                               help='Overwrite the output file, if it exists. The default behavior is to ask the user '
                                    'if it should be overwritten.')
    clobber_group.add_argument('-n', '--no-clobber', action='store_true',
                               help='Do not overwrite an existing output file. This is the default behavior.')

    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase logging to terminal')
    parser.add_argument('-q', '--quiet', action='store_const', const=-1, dest='verbose', help='Suppress all logging to terminal')

    if argstring is not None:
        args = parser.parse_args(argstring.split())
    else:
        args = parser.parse_args()

    return vars(args)


def driver(bib_files, output_file=_default_merged_file, exclude=[], clobber=False, no_clobber=False,
           conflict_mode='ask', interactive_remove=False, verbose=0):
    if os.path.isfile(output_file):
        if no_clobber:
            print('Output file ({}) exists, stopping'.format(output_file), file=sys.stderr)
            return
        elif not clobber:
            if not uiel.user_input_yn('Output file ({}) exists, overwrite?'.format(output_file), default='n'):
                print('Stopping', file=sys.stderr)
        # If clobber is true, pass through, the file will be overwritten if no errors occur
    base_bib = bu.init_bib_database(bib_files[0], no_backup=True, update_home=False)
    excluded_keys = list_excluded_keys(exclude)
    merge_bib_files(base_bib, bib_files[1:], excluded_keys, exclude_interactive=interactive_remove,
                    conflict_behavior=conflict_mode, verbose=verbose)
    remove_excluded_bib_keys(base_bib, excluded_keys, ask_to_remove=interactive_remove, verbose=verbose)
    base_bib.save_to_file(output_file)


def main():
    args = parse_args()
    driver(**args)

if __name__ == '__main__':
    main()