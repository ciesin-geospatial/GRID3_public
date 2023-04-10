"""match fields from two tables

these columns will be added to output input table (it_out_table_name)
>> *_updated : This is final match column. If match result=="YES", it_poi_name from input table
    will be replaced with mt_poi_name from match table (mt_out_table_name). Otherwise it_poi_name will be kept.
    Basicly this field combination if it_poi_name from input table and mt_poi_name from match table
>> *_match_name : Closest name from match table match to input table
>> *_match_uuid : unique id of mt_poi_name from match table.This field can be used to join input and match table
>> *_match_result : Indicates if match result good or bad. YES indicates good match ( generally over  80% match),
    NO indicates bad match ( generally less  80% match)
>> *_match_score: % match between it_poi_name and mt_poi_name. Will be safe check match sore between 70-85 % manually
    regardless of match_result
>> *_match_type :Indicates fuzzy match method. Partial matches are less confident. Will be safe check partial matches
    manually regardless of match_result
>> one_to_many_dup:Indicates a name from input table match two more than a name from match table.
>> many_to_one_dup:Indicates more than a name from match table match to a name from input table

Process description:
     We want to match entries between an input table and a candidate table.
     We have five(six) columns we match against - name (poi) admin 1, admin 2, type, location(lat,long)
     a first pass looks at just those in a similar vicinity and matches those.
     We use a fuzzy matching process to best match similar names
     Our first two match passes find rows in both tables with the same admin 1 and admin 2 values
     we then look for name (poi) matches within those two windows.
     As we find matching records between the input and candidate table we remove matched candidates
     in the end we then attempt top resolve duplicate matches (one to many or many to one)
     all rows in the input and output table are kept, with markings added to show where we matched and how
"""
from matching.matching_utilities import *
from utilities.utilities import *
import os.path
import configparser
import fiona


def main(config_file=None, config=None):

    # load config
    if config is None:
        if config_file is None:
            config_file = check_config_override("matching_config.ini")

        config = configparser.ConfigParser()
        config.read(config_file)
    else:
        config_file = "config_obj"

    try:
        config = config['inputs']
        it_input_dir = config['it_input_dir']
        it_input_filename = config['it_input_filename']
        it_output_dir = config['it_output_dir']
        it_output_filename = config['it_output_filename']
        it_poi_name = config['it_poi_name']
        it_poi_type = config['it_poi_type']
        it_id = config['it_id']
        it_admin1 = config['it_admin1']
        it_admin2 = config['it_admin2']
        it_lat = config['it_lat']
        it_long = config['it_long']

        mt_input_dir = config['mt_input_dir']
        mt_input_filename = config['mt_input_filename']
        mt_output_dir = config['mt_output_dir']
        mt_output_filename = config['mt_output_filename']
        mt_poi_name = config['mt_poi_name']
        mt_poi_type = config['mt_poi_type']
        mt_admin1 = config['mt_admin1']
        mt_admin2 = config['mt_admin2']
        mt_lat = config['mt_lat']
        mt_long = config['mt_long']

        match_by_distance = config['match_by_distance'].lower() == 'true'
        match_distance_m = int(config['match_distance_m'])

    except KeyError as ke:
        print("Can't find section or key '" + ke.args[0] + "' in config file '" + config_file + "'")
        return()

    # build our full filenames to load
    it_input_full_filename = os.path.join(it_input_dir, it_input_filename)
    mt_input_full_filename = os.path.join(mt_input_dir, mt_input_filename)

    # build our full filenames to save
    it_output_full_filename = os.path.join(it_output_dir, it_output_filename)
    mt_output_full_filename = os.path.join(mt_output_dir, mt_output_filename)

    # check if arcgis is needed and if so is loaded
    if get_file_type(it_output_full_filename) == "feature" or get_file_type(mt_output_full_filename) == "feature":
        import importlib
        arcgis_found = importlib.util.find_spec("arcgis") is not None

        if not arcgis_found:
            abort("Can't save feature files if arcgis is not present in environment")

    # make sure everything exists
    if not os.path.exists(it_output_dir):
        abort("can't save output - input table output directory doesn't exists: " + str(it_output_dir))

    if not os.path.exists(mt_output_dir):
        abort("can't save output - match table output directory doesn't exists: " + str(mt_output_dir))
    # check for input files
    if get_file_type(it_input_full_filename) == "feature":
        all_layers = fiona.listlayers(it_input_dir)
        if it_input_filename not in all_layers:
            abort("can't load input feature, file doesn't exists: " + str(it_input_full_filename))
    else:
        if not os.path.isfile(it_input_full_filename):
            abort("can't load input, file doesn't exists: " + str(it_input_full_filename))
    # now check for match files
    if get_file_type(mt_input_full_filename) == "feature":
        all_layers = fiona.listlayers(mt_input_dir)
        if mt_input_filename not in all_layers:
            abort("can't load input feature, file doesn't exists: " + str(mt_input_full_filename))
    else:
        if not os.path.isfile(mt_input_full_filename):
            abort("can't load input, file doesn't exists: " + str(mt_input_full_filename))

    # if directory contains gdm make sure our filename has no extension and isn't fc
    if ".gdb" in it_output_dir:
        it_output_full_filename = it_output_full_filename.replace(".fc", "")
    
    if ".gdb" in mt_output_dir:
        mt_output_full_filename = mt_output_full_filename.replace(".fc", "")

    # =========PROCESSING============= #
    # a variable to hold all match candidates from math_table
    match_table_all = None

    # read tables
    print("Reading input and match table...")
    input_table = read_data(it_input_full_filename, lat=it_lat, long=it_long)
    match_table = read_data(mt_input_full_filename, lat=mt_lat, long=mt_long)

    print("Input table length:" + str(len(input_table)))
    print("Match table length:" + str(len(match_table)))

    # create a dummy admin1 column  if type not exist in the tables
    if it_admin1 not in input_table.columns:
        print("Creating dummy admin1 field")
        it_admin1 = "dummy_admin1"
        input_table[it_admin1] = it_admin1
        mt_admin1 = it_admin1
        match_table[mt_admin1] = mt_admin1

    # create a dummy admin1 column  if type not exist in the tables
    if it_admin2 not in input_table.columns:
        print("Creating dummy admin2 field")
        it_admin2 = "dummy_admin2"
        input_table[it_admin2] = it_admin2
        mt_admin2 = it_admin2
        match_table[mt_admin2] = "dummy_admin2"

    # create a dummy type column if type not exist in the tables
    if it_poi_type not in input_table.columns:
        print("Creating dummy type field")
        it_poi_type = "dummy_type"
        input_table[it_poi_type] = it_poi_type
        mt_poi_type = it_poi_type
        match_table[mt_poi_type] = mt_poi_type

    # create a unique id(it_id) field if it doesn't exist in the input table
        if it_id not in input_table.columns:
            input_table['new_id'] = range(1, 1 + input_table.shape[0])

    # if it_poi_name==mt_poi_name change mt_poi_name to mt_mt_poi_name
    if it_poi_name == mt_poi_name:
        match_table.rename({mt_poi_name: "mt_" + mt_poi_name}, axis=1, inplace=True)
        mt_poi_name = "mt_" + mt_poi_name

    # ===========  MATCH withing a DISTANCE =================== #

    if match_by_distance:
        print(" ## Matching by distance ## ")

        input_table = fuzzy_match_within_distance(input_table, it_id, it_poi_name, match_table, mt_poi_name,
                                                  fields_to_create_uuid=[mt_admin1, mt_admin2, mt_poi_name,
                                                                         mt_poi_type],
                                                  match_distance_m=match_distance_m)

        # get match cases by distance
        input_matched_by_distance_yes = \
            input_table[input_table[it_poi_name + '_match_result'] == "YES"].reset_index(drop=True)

        # keep match table will all names to flag matched and unmatched cases at the end of process
        match_table_all = match_table.copy(deep=True)

        # exclude matching candidates from match table if it is already match in order to avoid duplicate match
        match_uuids = input_table[input_table[it_poi_name + '_match_score'] >= 90][it_poi_name + "_match_uuid"].tolist()
        match_table = match_table[~match_table[mt_poi_name + "_uuid"].isin(match_uuids)]

    else:
        # create empty table if match_by_distance == False
        input_matched_by_distance_yes = pd.DataFrame()

    # ===========  MATCH by ADMIN WINDOWS =================== #
    if it_poi_name + '_match_result' in input_table.columns:
        input_dist_no = input_table[input_table[it_poi_name + '_match_result'] == "NO"]
    else:
        input_dist_no = input_table

    print("Orig Input table size:", str(len(input_dist_no)))

    # match admin1 column (this also assigns uuids)
    print(" ## Matching admin1s ## ")
    fuzzy_match(input_dist_no, it_admin1, match_table, mt_admin1, None,
                match_level="", input_table_level_vars=[],
                match_table_level_vars=[])

    # match admin2 column in admin 1 window (this also assigns uuids)
    print(" ## Matching admin2s ## ")
    fuzzy_match(input_dist_no, it_admin2, match_table, mt_admin2, None,
                match_level="admin1", input_table_level_vars=[it_admin1 + "_updated"],
                match_table_level_vars=[mt_admin1 + "_cleaned"])

    # === match poi in admin2 window (this also assigns uuids) === #
    print(" ## Matching by admin2 window ## ")
    input_dist_no_a2_yes = input_dist_no[input_dist_no[it_admin2 + '_match_result'] == "YES"]

    fuzzy_match(input_dist_no_a2_yes, it_poi_name, match_table, mt_poi_name, mt_poi_type,
                match_level="admin2", input_table_level_vars=[it_admin1 + '_updated', it_admin2 + '_updated'],
                match_table_level_vars=[mt_admin1 + '_cleaned', mt_admin2 + '_cleaned'])

    # if we didn't already save a copy do so now.  Note this must be done after a fuzzymatch has set columns
    if match_table_all is None:
        match_table_all = match_table.copy(deep=True)

    # get inputs matched at the admin2 window
    input_dist_no_a2_yes_pass1_yes = input_dist_no_a2_yes[
        input_dist_no_a2_yes[it_poi_name + '_match_result'] == "YES"]

    # get inputs not matched at the admin2 window first pass
    input_dist_no_a2_yes_pass1_no = input_dist_no_a2_yes[
        input_dist_no_a2_yes[it_poi_name + '_match_result'] == "NO"]

    print(" ## Dedupe in admin2 window ## ")

    if match_by_distance:
        one_to_many_match_resolve_by_distance(input_dist_no_a2_yes_pass1_yes, it_poi_name + "_match_uuid",
                                              it_poi_name + '_match_result', it_lat, it_long, match_table_all,
                                              mt_poi_name + "_uuid", mt_lat, mt_long)

    # expand our ont to many to have a row for each pair
    expanded_pass1_table = expand_a_table(input_dist_no_a2_yes_pass1_yes, it_poi_name + "_match_uuid", how_to_split="/")

    # de-dup one to man and many to one
    resolve_dup_match_by_attribute(expanded_pass1_table, it_id, it_poi_name + "_match_uuid", "match_uuid_expand",
                                   it_poi_name + '_match_result', [it_admin1, it_admin2, it_poi_type], match_table_all,
                                   mt_poi_name + "_uuid", [mt_admin1, mt_admin2, mt_poi_type])

    resolve_duplicates_by_best_match(expanded_pass1_table, 'match_uuid_expand', it_id, it_poi_name + '_match_type',
                                     it_poi_name + '_match_score', it_poi_name + '_match_result')

    # get the ids we need
    pass1_dedupe_no_ids = expanded_pass1_table[
        expanded_pass1_table[it_poi_name + '_match_result'] == "NO"][it_id].unique().tolist()

    pass1_dedupe_yes_ids = expanded_pass1_table[
        expanded_pass1_table[it_poi_name + '_match_result'] == "YES"][it_id].unique().tolist()

    # exclude matching candidates from match table if it is matched with score over 90 in order to avoid duplicate match
    # this could be improved by doing both yes and >90 conditionals in one pass
    input_dist_no_a2_yes_match_still_yes = \
        expanded_pass1_table[expanded_pass1_table[it_poi_name + '_match_result'] == "YES"]
    match_uuids = input_dist_no_a2_yes_match_still_yes[
        input_dist_no_a2_yes_match_still_yes[it_poi_name + '_match_score'] >= 90][it_poi_name + "_match_uuid"].tolist()

    match_table = match_table[~match_table[mt_poi_name + "_uuid"].isin(match_uuids)]
    print("Match table length after dedupe:" + str(len(match_table)))

    print(" ## Pass 2 in admin2 window ## ")

    # reform input file to pass back in, use original with uuids from yes then no
    input_dist_no_a2_yes_pass2 = input_dist_no[input_dist_no[it_admin2 + '_match_result'] == "YES"]
    input_dist_no_a2_yes_pass2 = \
        input_dist_no_a2_yes_pass2[input_dist_no_a2_yes_pass2[it_id].isin(pass1_dedupe_no_ids)]

    # run pass 2 of admin 2 window
    if input_dist_no_a2_yes_pass2.shape[0] > 1:
        fuzzy_match(input_dist_no_a2_yes_pass2, it_poi_name, match_table, mt_poi_name, mt_poi_type,
                    match_level="admin2", input_table_level_vars=[it_admin1 + '_updated', it_admin2 + '_updated'],
                    match_table_level_vars=[mt_admin1 + '_cleaned', mt_admin2 + '_cleaned'])

        # remove pass 2 matches from candidates
        match_uuids = input_dist_no_a2_yes_pass2[
            input_dist_no_a2_yes_pass2[it_poi_name + '_match_score'] >= 90][it_poi_name + "_match_uuid"].tolist()
        match_table = match_table[~match_table[mt_poi_name + "_uuid"].isin(match_uuids)]
        print("Match table length after pass 2:" + str(len(match_table)))

        # get our yeses and nos from pass_2
        input_dist_no_a2_yes_match_pass2_yes = input_dist_no_a2_yes_pass2[
            input_dist_no_a2_yes_pass2[it_poi_name + '_match_result'] == "YES"]

        input_dist_no_a2_yes_match_pass2_no = input_dist_no_a2_yes_pass2[
            input_dist_no_a2_yes_pass2[it_poi_name + '_match_result'] == "NO"]

    else:
        input_dist_no_a2_yes_match_pass2_yes = pd.DataFrame()
        input_dist_no_a2_yes_match_pass2_no = pd.DataFrame()

    input_dist_no_a2_yes_pass1_orig_yes = \
        input_dist_no_a2_yes_pass1_yes[input_dist_no_a2_yes_pass1_yes[it_id].isin(pass1_dedupe_yes_ids)]

    # combine our original nos with our pass 2 nos
    input_dist_no_a2_yes_match_no = \
        pd.concat([input_dist_no_a2_yes_pass1_no, input_dist_no_a2_yes_match_pass2_no]).reset_index(drop=True)

    # match in admin1 window, use everything that wasn't in a2 window or failed to match there
    print(" ## Matching by admin1 window ## ")
    input_dist_no_a2_no = input_dist_no[input_dist_no[it_admin2 + '_match_result'] == "NO"]
    input_dist_no_a2_no_a1_yes = \
        pd.concat([input_dist_no_a2_no, input_dist_no_a2_yes_match_no]).reset_index(drop=True)

    # run admin 1 window
    if input_dist_no_a2_no_a1_yes.shape[0] > 1:
        fuzzy_match(input_dist_no_a2_no_a1_yes, it_poi_name, match_table, mt_poi_name, mt_poi_type,
                    match_level="admin1", input_table_level_vars=[it_admin1 + '_updated'],
                    match_table_level_vars=[mt_admin1 + '_cleaned'])

    # ===================== MERGE RESULT ================= #
    print("Merging all match results...")
    merge_all = pd.concat([input_matched_by_distance_yes, input_dist_no_a2_yes_pass1_orig_yes,
                           input_dist_no_a2_yes_match_pass2_yes, input_dist_no_a2_no_a1_yes]).reset_index(drop=True)

    print("Merged input length:" + str(len(merge_all)))

    # =================== REAVALUATE DUPLICATE MATCH ==================== #
    print("Resolving duplicate matches...")
    merge_all[it_poi_name + "_match_uuid"].fillna(" ", inplace=True)
    merge_all['orig_result'] = merge_all[it_poi_name + '_match_result']

    # expand our one to many out with a row per pair
    merge_all = expand_a_table(merge_all, it_poi_name + "_match_uuid", how_to_split="/")

    print("Expanded input length:" + str(len(merge_all)))
    print("Match_table_all length:" + str(len(match_table_all)))

    # resolve distance dupes first
    if match_by_distance:

        resolve_dup_match_by_distance(merge_all, it_id, "match_uuid_expand", it_poi_name + '_match_result', it_lat,
                                      it_long, match_table_all, mt_poi_name + "_uuid", mt_lat, mt_long)

        # calculate distance between match cases
        calculate_distance_between_matches(merge_all, it_id, "match_uuid_expand", it_lat, it_long,
                                           match_table_all, mt_poi_name + "_uuid", mt_lat, mt_long)

    resolve_dup_match_by_attribute(merge_all, it_id, it_poi_name + "_match_uuid", "match_uuid_expand",
                                   it_poi_name + '_match_result', [it_admin1, it_admin2, it_poi_type], match_table_all,
                                   mt_poi_name + "_uuid", [mt_admin1, mt_admin2, mt_poi_type])

    # resolve duplicates by match results
    resolve_duplicates_by_best_match(merge_all, 'match_uuid_expand', it_id, it_poi_name + '_match_type',
                                     it_poi_name + '_match_score', it_poi_name + '_match_result')

    # =======FLAG DUPLICATE MATCHES======== #
    # one to many duplicate match count
    merge_all = get_duplicate_count(merge_all, fields_to_check_dup=["match_uuid_expand"], out_field="one_to_many_dup")

    # many to one duplicate match count
    merge_all = get_duplicate_count(merge_all, fields_to_check_dup=[it_id], out_field="many_to_one_dup")

    print(" ## Overall result ## ")
    merge_all_yes = merge_all[merge_all[it_poi_name + '_match_result'] == "YES"].shape[0]
    merge_all_no = merge_all[merge_all[it_poi_name + '_match_result'] == "NO"].shape[0]

    # final summary
    print(f' Match count : {merge_all_yes}')
    print(f' Not Match count : {merge_all_no}')

    # ========== EXPORT RESULT ============== #
    print("Exporting output tables...")
    # delete created dummy variables in the input table
    delete_columns = [col for col in merge_all.columns if col.startswith("dummy")]
    delete_columns = delete_columns + ["match_rank", "max_r", "max"]
    merge_all.drop(delete_columns, axis=1, inplace=True, errors="ignore")

    it_output_full_filename = write_data(merge_all, it_output_full_filename)
    print(f"input table match result is saved here: {it_output_full_filename}")

    # flag not match cases in match table
    match_uuids = merge_all[merge_all[it_poi_name + '_match_result'] == "YES"]["match_uuid_expand"].tolist()
    match_table_all.loc[match_table_all[mt_poi_name + "_uuid"].isin(match_uuids), "ismatch"] = "YES"
    match_table_all.loc[~match_table_all[mt_poi_name + "_uuid"].isin(match_uuids), "ismatch"] = "NO"

    # delete created dummy variables in the match table
    delete_columns = [col for col in match_table_all.columns if col.startswith("dummy")]
    match_table_all.drop(delete_columns, axis=1, inplace=True, errors="ignore")

    mt_output_full_filename = write_data(match_table_all, mt_output_full_filename)
    print(f"Match table match result is saved here: {mt_output_full_filename}")


if __name__ == '__main__':
    main()
