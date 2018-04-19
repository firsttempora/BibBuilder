import argparse
import bibtexparser
from collections import OrderedDict
from copy import deepcopy
import re
import shutil

import pdb

#TODO: make a way to add links to years at the top of the page, marked by link start/link end

bib_start = '<!--START BIB-->'
bib_end = '<!--END BIB-->'
link_start = '<!--START LINKS-->'
link_end = '<!--END LINKS-->'


year_header_formats = {'std': '<h3>{0}</h3>',
                       'bootstrap': '<h3><span class="badge badge-dark">{0}</span></h3>'}


class EntryFormatter:
    def __init__(self, format_spec, connector=', ', terminator='.', bold_authors=None, latex2html=True):
        self._format_spec = format_spec
        self._connector = connector
        self._terminator = terminator

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
        fmt_string = self._prepare_fmt_string(entry.keys())
        return fmt_string.format(**entry)

    def add_bold_authors(self, *authors):
        self._bold_authors += authors

    def _prepare_fmt_string(self, available_keys):
        # Search the format string for instances of {key}, check if "key" is one of the keys available in the entry
        # dict. If not, remove everything between the start of the missing key and the next key
        key_re = re.compile(r'(?<=\{)\w+(?=\})')
        fmt_pieces = []
        for piece in self._format_spec:
            key = key_re.search(piece)
            if key is None:
                # No key, something went wrong
                raise ValueError('Each entry in the format specification must contain the substring {key} where key is a bib field (e.g. author, title, year)')
            elif key.group() in available_keys:
                fmt_pieces.append(piece)

        return self._connector.join(fmt_pieces) + self._terminator

    def _preprocess_entry(self, entry):
        entry = deepcopy(entry)
        if 'author' in entry.keys():
            entry['author'] = self._format_authors(entry['author'])
        if 'title' in entry.keys():
            entry['title'] = self._format_title(entry['title'])
        if 'pages' in entry.keys():
            entry['pages'] = self._format_pages(entry['pages'])
        if 'doi' in entry.keys():
            entry['doi'] = self._format_doi(entry['doi'])
        if 'url' in entry.keys():
            formatted_url = self._format_url(entry['url'])
            entry['url'] = formatted_url
            if 'doi' not in entry.keys():
                # If a DOI isn't available, insert a URL in its place
                entry['doi'] = formatted_url
        return entry

    def _format_authors(self, authors):
        authors = [bibtexparser.customization.splitname(a.strip()) for a in authors.split('and')]
        author_string = ''
        fmt_string = '{otag}{von} {last} {jr}, {first}{ctag}'
        for idx, auth in enumerate(authors):
            auth_joined = {k: ' '.join(v) for k, v in auth.items()}
            bold_tag = ('<strong>', '</strong>') if auth['last'][0] in self._bold_authors else ('', '')
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

        return self._strip_braces(author_string)

    def _format_title(self, title):
        # Right now, this is kind of a kluge assuming that my titles only have subscripts as e.g. $_2$ or $_{long}$
        # I should eventually figure out a more robust encoding
        title = re.sub(r'\$_\{?', '<sub>', title)
        title = re.sub(r'\$', '</sub>', title)

        # Remove any remaining braces. These are used in BibTex to keep capitalization and so are unnecessary here.
        # Should add a check that any braces aren't part of latex commands eventually.
        return self._strip_braces(title)

    def _format_pages(self, pages):
        # Replace a double dash with an emdash
        return re.sub('(?<=\d)--(?=\d)', '&mdash;', pages)

    def _format_doi(self, doi):
        if doi.startswith('10'):
            doi_url = 'https://doi.org/{}'.format(doi)
            doi = 'doi:' + doi
        elif doi.startswith('doi:10'):
            doi_url = 'https://doi.org{}'.format(doi.replace('doi:', ''))
        else:
            raise ValueError('A DOI value should either start with "10" or "doi:10"')

        return '<a href="{}" target="_blank">{}</a>'.format(doi_url, doi)

    def _format_url(self, url):
        return '<a href="{}" target="_blank">Link</a>'.format(url)

    @staticmethod
    def _strip_braces(s):
        s = s.replace('{', '')
        s = s.replace('}', '')
        return s


stdCitation = EntryFormatter(['{author}', '{title}', '<i>{journal}</i>', '<i>{volume}</i>', '{pages}', '{doi}', '{year}'])


def sort_bib_entries_by_year(bib_file, entry_type=None):
    with open(bib_file, 'r') as bib_obj:
        bib_dat = bibtexparser.load(bib_obj)

    if entry_type is None:
        entries = bib_dat.entries
    else:
        entries = [e for e in bib_dat.entries if e['ENTRYTYPE'] in entry_type]

    for e in entries:
        if 'year' not in e.keys():
            print('{} has no year'.format(e['ID']))

    years = sorted(set([e['year'] for e in entries]), reverse=True)

    #pdb.set_trace()

    entries_by_year = OrderedDict()
    for y in years:
        entries_by_year[y] = [e for e in entries if e['year'] == y]

    return entries_by_year


def insert_bib(html_file, bib_entries, formatter=stdCitation, year_fmt='std'):
    new_file = new_html_name(html_file)
    if year_fmt in year_header_formats.keys():
        year_fmt = year_header_formats[year_fmt]
    with open(html_file, 'r') as html_obj, open(new_file, 'w') as new_obj:
        in_bib = False
        for line in html_obj:
            if not in_bib:
                new_obj.write(line)
            if line.strip().startswith(bib_start):
                in_bib = True
                for year, entry_list in bib_entries.items():
                    # Add an anchor for the year
                    new_obj.write('<a name={0}></a>'.format(year))
                    # Write the year section header
                    new_obj.write(year_fmt.format(year) + '\n\n')
                    for entry in entry_list:
                        new_obj.write('<p>{}</p>\n\n'.format(formatter.format_entry(entry)))
            elif line.strip().startswith(bib_end):
                in_bib = False
                new_obj.write(line)


def new_html_name(html_name):
    return html_name + '.new'


def backup_name(name):
    return name + '.bak'


def move_files(html_file, do_backup=True):
    if do_backup:
        shutil.move(html_file, backup_name(html_file))

    shutil.move(new_html_name(html_file), html_file)


def parse_args():
    parser = argparse.ArgumentParser(description='Insert a bibliography in a website',
                                     epilog='The HTML file must contain the lines {} and {}, the bibliography will be '
                                            'placed between those lines. Anything already between them will be lost'.format(bib_start, bib_end))
    parser.add_argument('bib_file', help='The .bib file to read citations from')
    parser.add_argument('html_file', help='The .html file to insert the bibliography into')
    parser.add_argument('-a', '--author-bold', action='append', default=[], help='The last name of an author to make bold in the bibliography.'
                                                                     ' This option can be repeated to specify multiple authors.')
    parser.add_argument('-t', '--entry-type', action='append', help='The type of entry to include, e.g. "article" or "misc";'
                                                                    ' this is the part immediately after the @ in the bibtex file.'
                                                                    ' This option may be specified multiple times to include multiple'
                                                                    ' types of entry.')
    parser.add_argument('-y', '--year-fmt', default='<h3>{0}</h3>\n\n', help='The format string to use to print year section headers. This can be either a'
                                                                             'string that the format() method can insert one argument in, or one of the'
                                                                             ' strings "{}"'.format('", "'.join(year_header_formats.keys())))
    parser.add_argument('-b', '--no-backup', action='store_false', help='Do not create a backup of the old HTML file')

    return parser.parse_args()


def main():
    args = parse_args()
    stdCitation.add_bold_authors(*args.author_bold)
    entries = sort_bib_entries_by_year(args.bib_file, entry_type=args.entry_type)
    insert_bib(args.html_file, entries, year_fmt=args.year_fmt)
    move_files(args.html_file, do_backup=args.no_backup)


if __name__ == '__main__':
    main()