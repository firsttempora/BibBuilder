from bibtexparser import customization
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser
from doi2bib.crossref import get_bib_from_doi
from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError
import os
import re

import pdb

# This adapted from https://gist.github.com/januz/01e46431b94dee83c977
#doi_re = re.compile('10.(\d)+/([^(\s\>\"\<)])+')
# My turn. As far as I can tell from http://www.doi.org/doi_handbook/2_Numbering.html, there's very
# little restriction on suffixes, so I'm just going to look for a space
doi_re = re.compile('10.[\d\.]+/[^\s]+')


class DoiNotFoundError(Exception):
    pass


class BibRetrievalError(Exception):
    pass


class PdfParsingError(Exception):
    pass


class BetterBibDatabase(BibDatabase):
    def add_entry_by_string(self, bib_string, file_name=None, parser=None):
        # To ensure we get a properly formatted string, we'll parse it into a standard BibDatabase then steal
        # the entry from it
        if parser is None:
            parser = BibTexParser()
            parser.ignore_nonstandard_types = False
            parser.homogenise_fields = True
            parser.customization = format_entry
        tmpdat = parser.parse(bib_string)
        # We shouldn't need to do anything else. The other means of access entries (e.g. the dict) seem to be properties
        # created on the fly from the entries list. However, I'm going to take out the underscore in the ID because
        # underscores don't always play well in Latex
        tmpdat.entries[0]['ID'] = tmpdat.entries[0]['ID'].replace('_','')
        if file_name is not None:
            tmpdat.entries[0]['file'] = file_name

        self.entries.append(tmpdat.entries[0])

    def add_entry_by_file(self, pdf_file, **kwargs):
        bib_string = pdf2bib(pdf_file)
        self.add_entry_by_string(bib_string, file_name=pdf_file, **kwargs)


def format_entry(record):
    """
    Special customization function for BibTex entries
    :param record: the entry dict to modify
    :return: the modified dict
    """
    for key, value in record.items():
        record[key] = sanitize_html_strings(value)
    record = customization.page_double_hyphen(record)
    return record


def pdf2bib(pdf_file, verbosity=1):
    """
    Given a PDF file, tries to extract the paper's DOI and fetch the BibTex entry
    :param pdf_file: the path to the PDF file
    :return: The bibtex entry as a string
    """

    if not isinstance(pdf_file, str):
        raise TypeError('pdf_file must be a string')
    elif not os.path.isfile(pdf_file):
        raise IOError('pdf_file ({}) does not exist'.format(pdf_file))

    with open(pdf_file, 'rb') as pdf:
        try:
            pdf_obj = PdfFileReader(pdf)
            pdf_text = pdf_obj.getPage(0).extractText()
        except:
            raise PdfParsingError('Problem parsing {}. Likely this is an old PDF not amenable to parsing.'.format(pdf_file))
        doi_match = doi_re.search(pdf_text)

    if doi_match is None:
        raise DoiNotFoundError('No DOI found on first page of {}'.format(pdf_file))

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

    # Try to retrieve the bib string based on the doi
    success, bib_string = get_bib_from_doi(doi_string)
    if not success:
        raise BibRetrievalError('Could not retrieve bib string for {}'.format(pdf_file))

    return bib_string


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
    reg_exp = '{}(?P<subscript>.+){}'.format(re.escape('$\\less$sub$\\greater$'), re.escape('$\\less$/sub$\\greater$'))
    subscript = re.search(reg_exp, string)
    if subscript is not None:
        string = string.replace(subscript.group(), '$_{{{}}}$'.format(subscript.groupdict()['subscript'].strip()))

    # DOIs for some reason are getting '%2F' put instead of one of the slashes.
    string = string.replace('%2F', '/')

    return string