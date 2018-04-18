import argparse
import bibtexparser
from copy import deepcopy
import re

import pdb

bib_start = '<!--START BIB-->'
bib_end = '<!--END BIB-->'


class EntryFormatter:
    def __init__(self, format_string, bold_authors=None, latex2html=True):
        self._format_string = format_string

        if bold_authors is None:
            self._bold_authors = []
        elif isinstance(bold_authors, str):
            self._bold_authors = [bold_authors]
        elif isinstance(bold_authors, list):
            self._bold_authors = bold_authors
        else:
            raise TypeError('bold_authors must be a list, a string, or None')

        self._latex2html = latex2html

    def format_entry(self, entry):
        entry = self._preprocess_entry(entry)
        return self._format_string.format(**entry)

    def add_bold_authors(self, *authors):
        self._bold_authors += authors

    def _preprocess_entry(self, entry):
        entry = deepcopy(entry)
        entry['author'] = self._format_authors(entry['author'])
        # TODO: add format pages which replaces -- with em-dash
        # TODO: add format doi that prepends "doi:" if necessary and makes it a link to doi.org
        return entry

    def _format_authors(self, authors):
        authors = [bibtexparser.customization.splitname(a.strip()) for a in authors.split('and')]
        author_string = ''
        fmt_string = '{otag}{von} {last} {jr}, {first}{ctag}'
        for idx, auth in enumerate(authors):
            auth_joined = {k: ' '.join(v) for k, v in auth.items()}
            bold_tag = ('<strong>', '</strong>') if auth['last'] in self._bold_authors else ('', '')
            this_author = fmt_string.format(otag=bold_tag[0], ctag=bold_tag[1], **auth_joined)
            # After the first author, put the first name first
            fmt_string = '{otag}{first} {von} {last} {jr}{ctag}'

            # Clean up extra spaces. Clean up double spaces first so that if it leaves a > followed by a space,
            # that gets cleaned up too. We're removing spaces before commas, multiple spaces, spaces after HTML tags,
            # and spaces at the beginning or end
            this_author = re.sub(r'\s+(?=[,])', '', this_author)
            this_author = re.sub(r'(?<=[\s>])\s+', '', this_author).strip()

            author_string += this_author
            if idx < len(authors) - 1:
                author_string += ', '
            if idx == len(authors) - 2:
                author_string += 'and '

        return author_string


stdCitation = EntryFormatter('{author} ({year}), <i>{journal}</i>, <i>{volume}</i>, {pages}, {doi}.')


def sort_bib_entries_by_year(bib_file, entry_type=None):
    with open(bib_file, 'r') as bib_obj:
        bib_dat = bibtexparser.load(bib_obj)

    if entry_type is None:
        entries = bib_dat.entries
    else:
        entries = [e for e in bib_dat.entries if e['ENTRYTYPE'] == entry_type]

    years = sorted(set([e['year'] for e in entries]))

    entries_by_year = dict()
    for y in years:
        entries_by_year[y] = [e for e in entries if e['year'] == y]

    return entries_by_year


def insert_bib(html_file, bib_entries, formatter=stdCitation):
    new_file = html_file + '.new'
    with open(html_file, 'r') as html_obj, open(new_file, 'w') as new_obj:
        in_bib = False
        for line in html_obj:
            if not in_bib:
                new_obj.write(line)
            if line.strip().startswith(bib_start):
                in_bib = True
                for entry in bib_entries:
                    new_file.write('<p>{}</p>\n\n'.format(formatter.format_entry(entry)))
            elif line.strip().startswith(bib_end):
                in_bib = False
                new_obj.write(line)