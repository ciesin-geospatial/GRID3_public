"""
This scripts creates a spelling dictionary based on selected a set of words
please go over created output and remove words that are incorrectly misspelled
"""

from utilities.utilities import *
import configparser
from symspellpy import SymSpell


def main():
    # load config
    config_file = check_config_override("POI_processing_config.ini")

    config = configparser.ConfigParser()
    config.read(config_file)

    config_general = config['about_POI_table']

    dictionaries_dir = config_general['dictionaries_dir']
    poi_input_dir = config_general['poi_input_dir']

    area_of_interest = config_general['area_of_interest']
    poi_input_filename = config_general['poi_input_filename']

    poi_var_name = config_general['poi_var_name']
    type_dict_config = config['create_spelling_dictionary']
    old_spelling_dict_path = type_dict_config["old_spelling_dict_path"]

    poi_input_full_filename = os.path.join(poi_input_dir, poi_input_filename)
    type_dict_table_filename = os.path.join(dictionaries_dir, area_of_interest + "_type_dictionary.xlsx")
    out_table_filename = os.path.join(dictionaries_dir, area_of_interest + "_spelling_dictionary.xlsx")

    # read poi input table
    poi_df = read_data(poi_input_full_filename)

    # read word frequency table
    type_dict_df = read_data(type_dict_table_filename)

    # create type dictionary
    spelling_dict = generate_misspellings(poi_df, poi_var_name, type_dict_df, area_of_interest, min_length=4)

    # merge new and old type dictionary
    if (old_spelling_dict_path != "None") & (old_spelling_dict_path != ""):
        old_spelling_dict = read_data(old_spelling_dict_path)
        spelling_dict = pd.concat([spelling_dict, old_spelling_dict]).reset_index(drop=True)
        spelling_dict.drop_duplicates(["Word", "Misspelling"], inplace=True)

    # export
    write_data(spelling_dict, out_table_filename)
    print(f"Spelling dictionary table created and saved here: {out_table_filename}")


0


def generate_misspellings(df, input_column, type_dict, admin_name, skip_spellings=[], min_length=5):
    """
    :param df:  input dataframe
    :param input_column: Name of the field to extract type info
    :param type_dict: type dictionary
    :param admin_name: name of the admin. It can be a country name, district name or province name
    :param skip_spellings:
    :param min_length:
    :return: dataframe containing misspellings
    """

    # get a list of each seperate word in the type dictionary
    type_dict = type_dict[type_dict.type.notnull()]
    type_keywords = ' '.join(list(type_dict['type'].str.lower())).split()

    # convert from list to set to remove repeating words, can use as a set
    type_keywords_all = set(type_keywords)

    # keep only keywords with the minimum length
    type_keywords_to_check = [word for word in type_keywords_all if len(word) >= min_length]

    preclean(df, input_column, "clean_name")

    names = ' '.join(list(df[~pd.isna(df["clean_name"])]["clean_name"].str.lower())).split()
    columns = ['name', 'word', 'misspelling', 'frequency', 'score']
    results = pd.DataFrame()
    for word in type_keywords_to_check:
        # keep just words that start with the same letter as the type keyword
        # and have length at least half of the length of the type keyword
        # also remove the words that already appear in type keywords
        start_char = word[0]  # first letter
        min_len = len(word) // 2  # minimum length requirement
        names_word = [name for name in names if name.startswith(start_char)
                      and len(name) > min_len and name not in type_keywords_all]

        # write the relevant words to a text file
        filename = "temp-dictionary- " + word + ".txt"
        file1 = open(filename, "w")
        file1.write(' '.join(names_word))
        file1.close()

        # generate word frequency dictionary
        sym_spell = SymSpell()
        sym_spell.create_dictionary(filename)
        freq_dict = sym_spell.words
        # remove the text file
        os.remove(filename)

        # compute similarity score with respect to the original word
        threshold = (len(word) - 1) / len(word)  # score threshold
        for spelling, frequency in freq_dict.items():
            if spelling in skip_spellings:
                continue
            ratio = fuzz.ratio(spelling, word)
            if ratio / 100 >= threshold:
                new_row = pd.DataFrame([[admin_name, word, spelling, frequency, ratio]], columns=columns)
                results = pd.concat([results, new_row])

    if results.shape[0] > 0:
        results['name'] = results['name'].str.upper()
    # reset and drop index
    results.reset_index(inplace=True, drop=True)
    return results


if __name__ == '__main__': main()
