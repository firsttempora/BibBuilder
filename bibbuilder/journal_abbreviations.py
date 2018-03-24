import re

# List journals here, with the full name as the key and the abbreviation as the value.
# Try to keep them in alphabetical order.
# Omit "The" from the beginning of journals, the function below will remove it from any
# names given
abbrev_dict = {'Aerosol Science and Technology': 'Aerosol Sci. Technol.',
               'American Journal of Physical Anthropology': 'Am. J. Phys. Anthropol.',
               'Applied Optics': 'Appl. Opt.',
               'Atmospheric Chemistry and Physics': 'Atmos. Chem. Phys.',
               'Atmospheric Chemistry and Physics Discussions': 'Atmos. Chem. Phys. Discuss.',
               'Atmospheric Environment': 'Atmos. Environ.',
               'Atmospheric Measurement Techniques': 'Atmos. Meas. Tech.',
               'Atmospheric Measurement Techniques Discussions': 'Atmos. Meas. Tech. Discuss.',
               'Atmospheric Research': 'Atmos. Res.',
               'Chemical Reviews': 'Chem. Rev.',
               'Climatic Change': 'Clim. Change',
               'Earth-Science Reviews': 'Earth Sci. Rev.',
               'Environmental Pollution': 'Environ. Pollut.',
               'Environmental Science {\\&} Technology': 'Environ. Sci. Technol.',
               'Faraday Discussions': 'Faraday Discuss.',
               'Geophysical Research Letters': 'Geophys. Res. Lett.',
               'Geoscientific Model Development': 'Geosci. Model Dev.',
               'Geoscientific Model Development Discussions': 'Geosci. Model Dev. Discuss.',
               'Journal of Applied Meteorology and Climatology': 'J. Appl. Meterol. Climatol.',
               'Journal of Chemical Education': 'J. Chem. Educ.',
               'Journal of Chemical Physics': 'J. Chem. Phys',
               'Journal of Geophysical Research: Atmospheres': 'J. Geophys. Res. Atmos.',
               'Journal of Physical Chemistry A': 'J. Phys. Chem. A',
               'Journal of Quantitative Spectroscopy and Radiative Transfer': 'J. Quant. Spectrosc. Radiat. Transfer',
               'Monthly Weather Review': 'Mon. Weather Rev.',
               'Nature': 'Nature',
               'Nature Chemistry': 'Nat. Chem',
               'Nature Climate Change': 'Nat. Clim. Change',
               'Nature Communications': 'Nat. Commun.',
               'Nature Geoscience': 'Nat. Geosci.',
               'Physica D: Nonlinear Phenomena': 'Physica D',
               'Plant and Soil': 'Plant Soil',
               'Proceedings of the National Academy of Sciences': 'PNAS',
               'Proceedings of the {IEEE}': 'Proc. IEEE',
               'Remote Sensing of Environment': 'Remote Sens. Environ.',
               'Science': 'Science',
               '{IEEE} Transactions on Geoscience and Remote Sensing': 'IEEE Trans. Geosci. Remote Sens.',
               '{PLoS} Biology': 'PLoS Biol.'}


def abbreviate_journal(journal_name):
    # Remove "The" from the beginning of journal names. The abbreviation lookup tool at
    # https://woodward.library.ubc.ca/research-help/journal-abbreviations/
    # usually omits it, so we will make it optional.
    journal_name = re.sub('The\s?', '', journal_name)
    if journal_name in abbrev_dict:
        return abbrev_dict[journal_name]
    else:
        return journal_name
