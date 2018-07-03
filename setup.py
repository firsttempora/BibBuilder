#!/usr/bin/env python
from setuptools import setup

setup(
    name='bibbuilder',
    version='0.2',
    packages=['bibbuilder', 'bibbuilder.tests', 'bibbuilder.scripts'],
    url='https://github.com/firsttempora/BibBuilder',
    classifiers=['License :: OSI Approved :: MIT License'],
    author='josh',
    author_email='first.tempora@gmail.com',
    description='A Python package of utilities for working with BibTex files',
    install_requires=['bibtexparser',
                      'doi2bib',
                      'PyPDF2',
                      'textui'],
    entry_points={
        'console_scripts': ['bb-merge=bibbuilder.scripts.merge_bib_files:main',
                            'bb-build=bibbuilder.scripts.bib_main:main',
                            'bb-web=bibbuilder.scripts.web_main:main']
    }
)
