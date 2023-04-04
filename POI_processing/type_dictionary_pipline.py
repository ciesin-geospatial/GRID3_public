"""
This scripts creates a type dictionary based on selected a set of words
please go over created output and remove type that are incorrect
"""

from utilities.utilities import *
import configparser


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
    type_dict_config = config['create_type_dictionary']
    old_type_dict_path = type_dict_config["old_type_dict_path"]

    poi_input_full_filename = os.path.join(poi_input_dir, poi_input_filename)
    word_frequency_table_filename = os.path.join(dictionaries_dir, area_of_interest + "_word_frequency_table.xlsx")
    out_table_filename = os.path.join(dictionaries_dir, area_of_interest + "_type_dictionary_table.xlsx")

    # read poi input table
    poi_df = read_data(poi_input_full_filename)

    # read word frequency table
    wft_df = read_data(word_frequency_table_filename)

    # create type dictionary
    type_dict = create_type_dict(poi_df, poi_var_name, wft_df, area_of_interest)

    # merge new and old type dictionary
    if old_type_dict_path != "None":
        old_type_dict = read_data(old_type_dict_path)
        type_dict = pd.concat([type_dict, old_type_dict]).reset_index(drop=True)
        type_dict.drop_duplicates(["type", "abbreviation"], inplace=True)

    # save data
    write_data(type_dict, out_table_filename)
    print(f"Type dictionary table created and saved here: {out_table_filename}")


def create_type_dict(df, input_column, word_frequency_table, admin_name):
    """
    :param df:  input dataframe
    :param input_column: Name of the field to extract type info
    :param word_frequency_table: Word frequency table with words that refer to type of facility
    :param admin_name: name of the admin. It can be a country name, district name or province name
    :return: dataframe with type info
    """

    key_words = word_frequency_table["words"].str.strip().tolist()

    preclean(df, input_column, "clean_name")

    for index, row in df.iterrows():
        name = df.at[index, "clean_name"].split()
        name_kept = [i for i in name if i not in key_words]
        df.at[index, "only_name"] = " ".join(name_kept)

    for index, row in df.iterrows():
        only_name = df.at[index, "only_name"].split(" ")
        full_name = df.at[index, "clean_name"].split(" ")
        name_kept = [i for i in full_name if i not in only_name]
        df.at[index, "only_type"] = " ".join(name_kept)

    # Export list of facility types
    type_count = df["only_type"].value_counts()
    type_count_df = pd.DataFrame(type_count).reset_index().rename({"only_type": "count", "index": "type"}, axis=1)
    type_count_df["area_of_interest"] = admin_name
    type_count_df["abbreviation"] = ""

    return type_count_df


if __name__ == '__main__': main()
