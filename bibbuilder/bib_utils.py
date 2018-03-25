import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser
from datetime import datetime as dtime
from doi2bib.crossref import get_bib_from_doi
from pylatexenc.latexencode import utf8tolatex
from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError
import os
import re
import shutil
import unicodedata

from .journal_abbreviations import abbreviate_journal

import pdb

# Geophysical Research Letters appararently does something REALLY WEIRD with spaces in their article, so treat GRL
# papers specially. We'll look for a DOI that doesn't always show up first in the text, but is easier to parse
grl_re = re.compile('(?<={})'.format(re.escape('GeophysicalResearchLetters\nRESEARCHLETTER\n')) + '10.[\d\.]+/[^\s]+?' + '(?=KeyPoint)')
agu_re = re.compile('(?<={})'.format(re.escape('RESEARCHARTICLE\n')) + '10.[\d\.]+/[^\s]+?' + '(?=KeyPoint)')

# My turn. As far as I can tell from http://www.doi.org/doi_handbook/2_Numbering.html, there's very
# little restriction on suffixes, so I'm just going to look for a space first. If that fails, then
# the problem may be that there's a period after it that isn't part of the DOI because it's at the
# end of a sentence.
all_doi_res = [re.compile('10.[\d\.]+/[^\s]+'),
               re.compile('10.[\d\.]+/[^\s]+(?=(\.\s|,))'),
               re.compile('(?<=doi:)10.[\d\.]+/[^\s]+'),  # repeat the last two, but require it be prefaced with "doi:"
               re.compile('(?<=doi:)10.[\d\.]+/[^\s]+(?=(\.\s|,))'),  # to rule out some false positives
               grl_re,
               agu_re]


class DoiNotFoundError(Exception):
    pass


class BibRetrievalError(Exception):
    pass


class PdfParsingError(Exception):
    pass


class BetterBibDatabase(BibDatabase):
    @property
    def files(self):
        return [el['file'] for el in self.entries if 'file' in el]

    @property
    def dois(self):
        return [el['doi'] for el in self.entries if 'doi' in el]

    def ids(self):
        return [el['ID'] for el in self.entries]

    def add_entry_by_string(self, bib_string, file_name=None, skip_if_file_exists=True, skip_if_doi_exists=False,
                            parser=None):
        """
        Add a new entry corresponding to a BibTex string.
        :param bib_string: a string giving the section in a BibTex file that would represent this reference.
        :param file_name: the name of a local file to include in the reference section. Optional.
        :param skip_if_file_exists: boolean, default is True, meaning that if a reference pointing to the same local
        file already exists in the database, this reference will not be added. Intended to make it easy to update a
        database without worrying about overwriting existing files.
        :param skip_if_doi_exists: boolean, default is False, but if True, do not add this reference if another
        reference with the same DOI already exists. Intended to avoid adding duplicate files.
        :param parser: An instance of bibtexparser.bparser.BibTextParser customized to parse the new string. The default
        parser is set with:
            * ignore_nonstandard_types = False
            * parser.homogenise_fields = True
            * parser.customization = lambda entry: self.format_entry(entry)
        thus, the custom parsing uses the format_entry method of this class with the instance of the class at the time
        this method was called.
        :return: none, adds entry in place.
        """
        if skip_if_file_exists and file_name is not None:
            if file_name in self.files:
                print('Not adding {}, already in .bib file'.format(file_name))
                return

        # To ensure we get a properly formatted string, we'll parse it into a standard BibDatabase then steal
        # the entry from it
        if parser is None:
            parser = BibTexParser()
            parser.ignore_nonstandard_types = False
            parser.homogenise_fields = True
            # Create a lambda function that knows about the current state of the database
            parser.customization = lambda entry: self.format_entry(entry)

        tmpdat = parser.parse(bib_string)

        if skip_if_doi_exists and 'doi' in tmpdat.entries[0] and tmpdat.entries[0]['doi'] in self.dois:
            return

        if file_name is not None:
            tmpdat.entries[0]['file'] = file_name

        # We shouldn't need to do anything else. The other means of access entries (e.g. the dict) seem to be properties
        # created on the fly from the entries list
        self.entries.append(tmpdat.entries[0])

    def add_entry_by_file(self, pdf_file, **kwargs):
        """
        Add an entry corresponding to a PDF file.
        :param pdf_file: the path to the PDF file.
        :param kwargs: additional key word arguments are passed through to add_entry_by_string(). See its documentation
        for a list
        :return: none
        """
        bib_string = pdf2bib(pdf_file)
        self.add_entry_by_string(bib_string, file_name=pdf_file, **kwargs)

    @staticmethod
    def load_from_file(bib_file):
        """
        Load a bibtex file as a database
        :param bib_file: the path to the .bib file as a string
        :return: the new database
        """
        with open(bib_file, 'r') as bib_obj:
            tmpdat = bibtexparser.load(bib_obj)
        bibdat = BetterBibDatabase()
        bibdat.entries = tmpdat.entries
        return bibdat

    def save_to_file(self, bib_file):
        """
        Save this database to a file.
        :param bib_file: the path to the file as a string. Note! Will be overwritten.
        :return: none
        """
        with open(bib_file, 'w') as bib_obj:
            bibtexparser.dump(self, bib_obj)

    def format_entry(self, record):
        """
        Special customization function for BibTex entries. Sanitizes HTML characters from any part of the entry, ensures
        that page ranges use two dashes, and abbreviates journals if possible.
        :param record: the entry dict to modify
        :return: the modified dict
        """
        for key, value in record.items():
            record[key] = sanitize_html_strings(value)

        record = bibtexparser.customization.page_double_hyphen(record)
        if 'journal' in record:
            record['journal'] = abbreviate_journal(record['journal'])

        # This should happen after we've sanitized the author string for miscellanceous HTML crud.
        record['ID'] = self.format_id(record)

        for key, value in record.items():
            if key != 'ID':
                # This needs to happen after we create the ID, because the id creation can remove accents from unicode
                # characters but not Latex accents. The non_ascii_only is needed to avoid escaping special Latex
                # characters already present, like with e.g. {NO}$_2$
                record[key] = utf8tolatex(record[key], non_ascii_only=True)

        return record

    def format_id(self, record):
        """
        Format a record's ID to avoid underscores and to be unique among the records already contained in the database.
        :param record_id: the record ID as a string
        :return: the modified record ID as a string
        """
        # I'm going to customize the id completely to be last name, first initial, year. This will cut down on duplicate
        # keys from people with the same last name
        first_author = record['author'].split(' and ')[0]
        first_author = bibtexparser.customization.splitname(first_author)
        # Each element of the first_author dict is a list
        record_id = '{}{}{}'.format(first_author['last'][0], first_author['first'][0][0], record['year'][-2:])
        # Strip out unicode characters. First try to remove accents, then just ignore non-ascii characters
        # Credit to https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string#518232
        record_id = ''.join([c for c in unicodedata.normalize('NFD', record_id) if unicodedata.category(c) != 'Mn'])
        # encode() gives a bytes string, then decode turns it back into a regular string. This feels awkward, but I'm
        # not sure at the moment what a more elegant way to handle this is.
        record_id = record_id.encode('ascii', 'ignore').decode('ascii')
        # Lastly remove any Latex commands, which start with a \ and go until the next non-letter character, and
        # anything between curly braces, which are probably random Latex symbols that should not be in the key
        record_id = re.sub('\\\\[a-zA-Z]+', '', record_id)
        record_id = re.sub('[^\w\-]', '', record_id)

        # Check if the current ID exists already. If it does, add a letter to the end to make it unique.
        all_ids = self.ids()
        if record_id not in all_ids:
            return record_id

        for letter in iter_letters('A', 'Z'):
            new_id = record_id + letter
            if new_id not in all_ids:
                return new_id

        raise RuntimeError('Ran out of possible suffixes for record ID "{}"'.format(record_id))


def shell_error(msg, exit_code=1):
    print(msg)
    exit(exit_code)


def get_pdf_page_text(pdf_file, page=0):
    if not isinstance(pdf_file, str):
        raise TypeError('pdf_file must be a string')
    elif not os.path.isfile(pdf_file):
        raise IOError('pdf_file ({}) does not exist'.format(pdf_file))

    with open(pdf_file, 'rb') as pdf:
        try:
            pdf_obj = PdfFileReader(pdf)
            pdf_text = pdf_obj.getPage(page).extractText()
        except:
            raise PdfParsingError('Problem parsing {}. Likely this is an old PDF not amenable to parsing.'.format(pdf_file))

    return pdf_text


def pdf2bib(pdf_file, verbosity=0):
    """
    Given a PDF file, tries to extract the paper's DOI and fetch the BibTex entry
    :param pdf_file: the path to the PDF file
    :return: The bibtex entry as a string
    """

    found_a_doi = False
    bib_string = ''

    pdf_text = get_pdf_page_text(pdf_file)

    # Try each of the regexes in sequence. Hopefully one will work.
    for doi_re in all_doi_res:
        doi_match = doi_re.search(pdf_text)
        # If we did not find a match, try the next one. If we did, make a note of that, because that
        # will affect the error we give if this fails.
        if doi_match is None:
            continue
        else:
            found_a_doi = True

        doi_string = doi_match.group(0)

        # Assume (for now) that the DOI suffix cannot include Unicode. This will stop the DOI at the first non-ASCII
        # character. Which corrects an issue with e.g. doi:10.5194/acp-11-8543-2011 where in the PDF the (c) symbol comes
        # right after the DOI and gets included
        last_idx = 0
        for idx, char in enumerate(doi_string):
            if ord(char) > 127:
                break
            else:
                last_idx = idx + 1
        doi_string = doi_string[:last_idx]

        if verbosity > 0:
            print('Looking up DOI {}'.format(doi_string))

        # Try to retrieve the bib string based on the doi. If we do so successfully, go ahead and return.
        # If not, then try the next regex. If there are none left, then we'll leave bib_string as an empty
        # string and raise the appropriate error.
        success, bib_string = get_bib_from_doi(doi_string)
        if success:
            break
        else:
            bib_string = ''

    if not found_a_doi:
        raise DoiNotFoundError('No DOI found on first page of {}'.format(pdf_file))
    elif len(bib_string) == 0:
        raise BibRetrievalError('Could not retrieve bib string for {}'.format(pdf_file))

    return bib_string


def fix_subscript(string, before_substring, after_substring):
    reg_exp = '{}(?P<subscript>.+){}'.format(re.escape(before_substring), re.escape(after_substring))
    subscript = re.search(reg_exp, string)
    if subscript is not None:
        string = string.replace(subscript.group(), '$_{{{}}}$'.format(subscript.groupdict()['subscript'].strip()))
    return string



def sanitize_html_strings(string):
    """
    Deals with quirks of converting HTML strings into appropriate Latex strings.
    :param string: string to be parsed
    :return: a cleaned up string
    """

    # This function is by necessity going to have a lot of special cases. I will add additional cases as they come up

    # The first case comes up in how ACP represents chemical names in titles. E.g.:
    #   'A high spatial resolution retrieval of {NO}$\\less$sub$\\greater$ 2$\\less$/sub$\\greater$ ...'
    # should just have '{NO}$_2$'
    string = fix_subscript(string, '$\\less$sub$\\greater$', '$\\less$/sub$\\greater$')

    # Another case in a 2018 ACP article title:
    #   'High-resolution quantification of atmospheric {CO}{\\&}lt$\\mathsemicolon$sub{\\&}gt$\\mathsemicolon$2{\\&}lt$\\mathsemicolon$/sub{\\&}gt$\\mathsemicolon$ mixing  ratios in the Greater Toronto Area, Canada'
    string = fix_subscript(string, '{\\&}lt$\\mathsemicolon$sub{\\&}gt$\\mathsemicolon$', '{\\&}lt$\\mathsemicolon$/sub{\\&}gt$\\mathsemicolon$')

    # DOIs for some reason are getting '%2F' put instead of one of the slashes.
    string = string.replace('%2F', '/')

    return string


def init_bib_database(bib_file, no_backup=False):
    """
    Initialize the BibTex database. If given file exist, back it up and read it in. If it does not exist, create an
    empty database.
    :param bib_file: the path to the .bib file to create or update.
    :param no_backup: boolean, if False (default) the bib file is backed up before being loaded (if it exists). If true,
    it is not backed up.
    :return: an instance of BetterBibDatabase.
    """
    if os.path.isfile(bib_file):
        if not no_backup:
            backup_bib_file(bib_file)
        return BetterBibDatabase.load_from_file(bib_file)
    else:
        return BetterBibDatabase()


def backup_bib_file(bib_file):
    file_path = os.path.dirname(bib_file)
    file_name, ext = os.path.splitext(os.path.basename(bib_file))
    backup_suffix = '-bckp-{}'.format(dtime.now().strftime('%Y%m%d-%H%M%S'))
    file_name += backup_suffix + ext
    shutil.copy(bib_file, os.path.join(file_path, file_name))


def iter_letters(start, stop):
    start_int = ord(start)
    end_int = ord(stop) + 1
    for i in range(start_int, end_int):
        yield chr(i)
