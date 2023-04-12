"""
This script separates types from a PoI name, fixes misspellings, reformat types and does basic checks.

These fields will be added to output table:
>> poi_out_var: PoI name without a type ( type will be removed based on type dictionary) and
    misspellings are fixed ( misspelled words will be fixed on spelling dictionary)
>> extract_type: types that extracted from specified poi_var_name
>> sub_type: formatted version of extracted types (types are  formatted based on type dictionary)
>> score: how well extracted types are formatted into sub_type. Score less than 80 needs manuel check
>> name_length: Count of characters in  poi_out_var. Long names need manuel check
>> type_length:Count of characters in  sub_type. Long types need manuel check
>> special_chrs:Special characters in the poi_out_var. Improper special characters need to be removed.
>> only_numeric : Names with only numerical values in the poi_out_var.
"""

import configparser
from dictionaries.dictionary_utilities import *
import fiona


def main(config_file=None, config=None):

    # load config
    if config is None:
        if config_file is None:
            config_file = check_config_override("POI_processing_config.ini")

        config = configparser.ConfigParser()
        config.read(config_file)
    else:
        config_file = "config_obj"

    try:
        config_general = config['about_POI_table']

        data_source = config_general['data_source']
        dictionaries_dir = config_general['dictionaries_dir']
        poi_input_dir = config_general['poi_input_dir']
        poi_input_filename = config_general['poi_input_filename']
        poi_output_dir = config_general['poi_output_dir']

        poi_lat_var = config_general['poi_lat_field']
        poi_long_var = config_general['poi_long_field']

        country_ISO = config_general['country_ISO']
        language_var = config_general['language']
        poi_name_field = config_general['poi_name_field']
        poi_type_field = config_general['poi_type_field']
        poi_data_type = config_general['poi_data_type']

        MAX_ADMIN_LEVELS = 5
        poi_admins = {}
        for lvl in range(1, MAX_ADMIN_LEVELS):
            poi_admins[lvl] = config_general['boundary' + str(lvl)]

        preprocessing1_config = config['preprocessing1']
        poi_output_extension_type = preprocessing1_config['poi_output_extension_type']

    except KeyError as ke:
        print("Can't find section or key '" + ke.args[0] + "' in config file '" + config_file + "'")
        return()

    poi_input_table_name_basename = poi_input_filename.split(".")[0]
    poi_output_table_name = poi_input_table_name_basename + "_preprocessing1" + poi_output_extension_type

    poi_input_full_filename = os.path.join(poi_input_dir, poi_input_filename)
    poi_output_filename = os.path.join(poi_output_dir, poi_output_table_name)

    pot_output_name_field, poi_output_type_field = get_poi_labels(poi_data_type)

    # make sure everything exists
    if not os.path.exists(poi_output_dir):
        abort("can't save output - output directory doesn't exists: " + str(poi_output_dir))

    if get_file_type(poi_input_full_filename) == "feature":
        all_layers = fiona.listlayers(poi_input_dir)
        if poi_input_filename not in all_layers:
            abort("can't load input, file doesn't exists: " + str(poi_input_full_filename))
    else:
        if not os.path.isfile(poi_input_full_filename):
            abort("can't load input, file doesn't exists: " + str(poi_input_full_filename))

    # read input table
    print("Loading data from " + poi_input_full_filename)
    if poi_lat_var != "":
        poi_df = read_data(poi_input_full_filename, poi_lat_var, poi_long_var)
    else:
        poi_df = read_data(poi_input_full_filename)

    col_list = [poi_name_field, poi_lat_var, poi_long_var] + list(poi_admins.values())
    sanity_check_df(poi_df, poi_input_filename, col_list)

    print("Placing processed poi '" + poi_name_field + "' in " + pot_output_name_field)

    print("Cleaning boundary names...")
    for lvl in range(1, MAX_ADMIN_LEVELS):
        if poi_admins[lvl] != "":
            print("\tboundary" + str(lvl) + " [" + poi_admins[lvl] + "] as " + lookup_admin_level(country_ISO, lvl))
            preclean(poi_df, poi_admins[lvl], lookup_admin_level(country_ISO, lvl), remove_accent=True)

    # Clean facility name
    print("Cleaning input variable...")
    preclean(poi_df, poi_name_field, "clean_name")

    # Correct name column with help of spelling dictionary
    print("Correcting spellings...")
    spelling_dict = get_spelling_dictionary(country_ISO, poi_data_type, dictionaries_dir)
    correct_spelling(poi_df, spelling_dict, "clean_name", "corrected_name")

    # get our type dict used below
    type_dict_df = get_type_dictionary_df(country_ISO, poi_data_type, dictionaries_dir)

    # Correct name column with help of spelling dictionary
    print("Correcting types...")
    clean_type_info(poi_df, type_dict_df, "corrected_name")

    # remove type from corrected name and place striped in output column
    print("Removing type from name...")
    remove_type_info(poi_df, type_dict_df, "corrected_name", pot_output_name_field)

    # extract type from corrected name into its own column
    print("Extract type from name...")
    extract_type(poi_df, "corrected_name", pot_output_name_field, "extract_type")

    # remap extracted type
    print("Mapping types...")
    map_type(poi_df, "extract_type", poi_output_type_field, "score", type_dict_df)

    # also do our original type
    print("Mapping types...")
    if poi_type_field != "":
        map_type(poi_df, poi_type_field, poi_output_type_field + "_orig", "score", type_dict_df)

    if language_var == "French" or language_var == "Portuguese":
        print("Updating types based on language...")
        fix_language(poi_df, poi_output_type_field, language_var)

    # add grid3 required fields
    print("Adding required GRID3 fields...")
    add_g3_required_fields(poi_df, data_source, country_ISO)

    # make simple check in cleaned facility name , and types
    print("Basic checks...")
    facility_sanity_checks(poi_df, pot_output_name_field, poi_output_type_field)

    # remove transitory columns
    poi_df.drop(["clean_name", "corrected_name"], inplace=True, axis=1, errors="ignore")

    # export
    print("Exporting data...")
    poi_output_filename = write_data(poi_df, poi_output_filename)
    print(f"Output table is saved here: {poi_output_filename}")


if __name__ == '__main__':
    main()
