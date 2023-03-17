"""This module provides access to a variety of convenience dictionaries
for processing points of interests in our files"""

from utilities.utilities import *
from dictionaries.country_dictionary import *


def lookup_admin_level(country_iso, level):
    if isinstance(level,int):
        level = "boundary"+str(level)
    elif not level.startswith("bound"):
        level = "boundary" + level
    return country_boundaries[country_iso][level]


def get_poi_labels(poi_dt):
    if poi_dt not in poi_data_type:
        return "g3_unknown", "g3_unknown_type"
    else:
        lbl = poi_data_type[poi_dt]
        return lbl, lbl + "_type"


def get_spelling_dictionary(country_iso, poi_type, dictionaries_dir=""):
    """ Load our spelling dictionary into a python dictionary of words to a list of misspellings.
    We load with pandas because they are in xlsx and it makes life easy.
    :param country_iso: iso code for the country dictionary we want
    :param poi_type: type of point we are looking for, health, settlement, well
    :param dictionaries_dir: directory to look for dictionaries (if not in default)
    :returns: python dictionary of words to misspellings
    """

    # if we aren't given an override build it.
    if dictionaries_dir == "":
        dictionaries_dir = os.path.join(os.path.dirname(__file__), poi_type)

    dict_filename = os.path.join(dictionaries_dir, country_iso + "_spelling_dictionary.xlsx")
    spelling_dict_df = read_data(dict_filename)

    # this assumes our dictionary file has "word" and "misspelling" columns.
    words_to_correct = spelling_dict_df['word'].unique()
    spelling_dict = {}

    for word in words_to_correct:
        spelling_dict[word] = list(spelling_dict_df[(spelling_dict_df['word'] == word)]['misspelling'])

    return spelling_dict


def get_type_dictionary_df(country_iso, poi_type, dictionaries_dir=""):
    """ Load our type dictionary into a dataframe.  Used in several ways so we just leave as DF
    :param country_iso: iso code for the country dictionary we want
    :param poi_type: type of point we are looking for, health, settlement, well
    :param dictionaries_dir: directory to look for dictionaries (if not in default)
    :returns: dataframe with type mappings
    """
    # if we aren't given an override build it.
    if dictionaries_dir == "":
        dictionaries_dir = os.path.join(os.path.dirname(__file__), poi_type)

    dict_filename = os.path.join(dictionaries_dir, country_iso + "_type_dictionary.xlsx")
    type_dict_df = read_data(dict_filename)

    return type_dict_df
