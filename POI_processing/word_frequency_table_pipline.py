"""
this script creates a word frequency table.
please go over the words in output table and only keep the words that refer type of a point of interest
correct spelling if there is any
"""

from utilities.utilities import *
import os
import pandas as pd
import configparser


def main():
    # load config
    config_file = "POI_processing_config.ini"

    config = configparser.ConfigParser()
    config.read(config_file)

    config_general = config['about_POI_table']
    dictionaries_dir = config_general['dictionaries_dir']
    poi_input_dir = config_general['poi_input_dir']

    area_of_interest = config_general['area_of_interest']
    poi_input_filename = config_general['poi_input_filename']
    poi_var_name = config_general['poi_var_name']
    wf_config = config['word-frequency']
    frequency_threshold = int(wf_config['frequency_threshold'])
    out_table_filename = area_of_interest + "_word_frequency_table.xlsx"

    poi_input_full_filename = os.path.join(poi_input_dir, poi_input_filename)
    poi_output_table = os.path.join(dictionaries_dir, out_table_filename)  # should use output type to determine?

    # read input table
    poi_df = read_data(poi_input_full_filename)

    # compute frequency and save file
    word_frequency_df = get_word_frequency(poi_df, poi_var_name, frequency_threshold=frequency_threshold)
    write_data(word_frequency_df, poi_output_table)
    print(f"Word frequency table created and saved here: {poi_output_table}")


def get_word_frequency(df, input_var, frequency_threshold=5):
    """
    :param df: inpute dataframe
    :param input_var: name of the field to create word frequency from
    :param frequency_threshold: frequency of a word to include into frequency table
    :return: dataframe with word and frequency columns
    """

    # preclean input_var
    preclean(df, input_var, "clean_name")

    # create frequency df
    word_count = df["clean_name"].str.split(expand=True).stack().value_counts()
    word_count_df = pd.DataFrame(word_count).reset_index().rename({0: "frequency", "index": "words"}, axis=1)
    word_count_df = word_count_df[word_count_df["frequency"] >= frequency_threshold]
    df.drop(["clean_name"], axis=1, inplace=True)
    return word_count_df


if __name__ == '__main__': main()
