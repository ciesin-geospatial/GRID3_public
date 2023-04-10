from utilities.utilities import *
import jellyfish
import rapidfuzz.string_metric
from rapidfuzz.distance import *


def create_phonetic_column(df, field, phonetic_code='nysiis', new_field_prefix=None, fillna_with_orig_field=True):
    """Creates a new column with a phonetic version of the source column

    :param df: dataframe to manipulate
    :param field: a field name to change
    :param phonetic_code: nysiis or soundex or mr_codex or metaphone
    :param new_field_prefix: a prefix to give output field otherwise phonetic code will be added to field name
    :param fillna_with_orig_field: True fill na in the output field with field
    :return: dataframe
    """

    # our possible phonetic codes, used for "eval" lookup below
    soundex = jellyfish.soundex  # 'J412'
    nysiis = jellyfish.nysiis  # 'JALYF'
    mr_codex = jellyfish.match_rating_codex  # 'JLLFSH'
    metaphone = jellyfish.metaphone  # 'JLFX'

    if new_field_prefix is None:
        new_field_prefix = field + '__'

    phonetic_func = eval(phonetic_code)
    df[new_field_prefix + phonetic_code] = \
        df[field].apply(lambda x: ' '.join([(w if w.isnumeric() else phonetic_func(w)) for w in x.split()])
        if isinstance(x, str) else np.nan).apply(lambda x: np.nan if not isinstance(x, str) or len(x) == 1 else x)

    if fillna_with_orig_field:
        df[new_field_prefix + phonetic_code].fillna(df[field], inplace=True)

    return df


def one_to_many_match_resolve_by_distance(input_table, match_name_uuid, match_result, input_table_lat, input_table_long,
                                          match_table, match_table_uuid, match_table_lat, match_table_long,
                                          distance_m=500):
    """
    :param input_table: dataframe
    :param match_name_uuid: match name unique uuid from match table
    :param match_result: yes/no
    :param input_table_lat: latitude
    :param input_table_long: longitude
    :param match_table: dataframe
    :param match_table_uuid: match name unique uuid from match table
    :param match_table_lat: latitude
    :param match_table_long: longitude
    :param distance_m: distance to check within (in meters)
    :return:
    """

    check_dup = input_table[(input_table[match_name_uuid].str.contains("/")) & (input_table[match_result] == "YES")]
    check_dup_group = check_dup.groupby(match_name_uuid)
    for i, group in check_dup_group:
        get_visit_lat = check_dup.loc[check_dup[match_name_uuid] == i][input_table_lat].values[0]
        get_visit_long = check_dup.loc[check_dup[match_name_uuid] == i][input_table_long].values[0]
        if not np.isnan(get_visit_lat):
            uuids = i.split("/")
            dist_dict = {}
            for uuid in uuids:
                get_mfl_lat = match_table.loc[match_table[match_table_uuid] == uuid][match_table_lat].values[0]
                get_mfl_long = match_table.loc[match_table[match_table_uuid] == uuid][match_table_long].values[0]
                distance = point_pairs_dist_calculation(get_visit_long, get_visit_lat, get_mfl_long, get_mfl_lat)
                dist_dict[uuid] = distance
            closest_uuid = min(dist_dict, key=dist_dict.get)
            if dist_dict[closest_uuid] <= distance_m:
                input_table.loc[input_table[match_name_uuid] == i, match_name_uuid] = closest_uuid
            elif dist_dict[closest_uuid] >= distance_m:
                input_table.loc[input_table[match_name_uuid] == i, match_name_uuid] = np.nan
                input_table.loc[input_table[match_name_uuid] == i, match_result] = "NO"


def one_to_many_match_resolve_by_attribute(input_table, match_name_uuid, input_table_list_of_fields_intersect,
                                           match_table, match_table_uuid, match_table_list_of_fields_intersect):
    """Recheck duplicate matches.
    :param input_table:dataframe
    :param match_name_uuid: match name uuid in the input table that attached from match table
    :param input_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    :param match_table: dataframe
    :param match_table_uuid: uuid
    :param match_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    :return: dataframe
    """

    input_table[match_name_uuid].fillna(" ", inplace=True)
    for i, row in input_table.iterrows():
        if "/" in row[match_name_uuid]:
            uuid_count_dict = {}
            uuids = row[match_name_uuid].split("/")
            from_input_table = {row[k] for k in input_table_list_of_fields_intersect}
            for uuid in uuids:
                match_table_select = match_table[match_table[match_table_uuid] == uuid][
                    match_table_list_of_fields_intersect]
                from_match_table = {match_table_select.iloc[0][j] for j in match_table_list_of_fields_intersect}
                intersect = from_input_table.intersection(from_match_table)
                uuid_count_dict[uuid] = len(intersect)
            all_values = uuid_count_dict.values()
            max_value = max(all_values)
            max_match = "/".join(dict(filter(lambda elem: elem[1] == max_value, uuid_count_dict.items())).keys())
            input_table.at[i, match_name_uuid] = max_match


def many_to_one_match_resolve_by_distance(input_table, unique_uuid, match_name_uuid, match_result,
                                          input_table_lat, input_table_long,
                                          match_table, match_table_uuid, match_table_lat, match_table_long,
                                          distance_m=500):

    uuid_list = input_table[input_table[match_result] == "YES"][match_name_uuid].tolist()
    dup_uuid_list = [item for item, count in Counter(uuid_list).items() if count > 1]
    print(f"There are  {len(dup_uuid_list)} many to one duplicate matches")

    for i in dup_uuid_list:
        if i != " ":
            match_lat = match_table.loc[match_table[match_table_uuid] == i][match_table_lat].values[0]
            match_long = match_table.loc[match_table[match_table_uuid] == i][match_table_long].values[0]
            if not np.isnan(match_long):
                dist_dict = {}
                input_table_uuid = input_table[input_table[match_name_uuid] == i][unique_uuid].tolist()
                for uuid in input_table_uuid:
                    get_lat = input_table.loc[input_table[unique_uuid] == uuid][input_table_lat].values[0]
                    get_long = input_table.loc[input_table[unique_uuid] == uuid][input_table_long].values[0]
                    distance = point_pairs_dist_calculation(match_long, match_lat, get_long, get_lat)
                    dist_dict[uuid] = distance
                closest_uuid = min(dist_dict, key=dist_dict.get)
                if dist_dict[closest_uuid] <= distance_m:
                    input_table_uuid.remove(closest_uuid)
                    input_table.loc[input_table[unique_uuid].isin(input_table_uuid), match_result] = "NO"


def many_to_one_match_resolve_by_attribute(input_table, unique_uuid, match_name_uuid, match_result,
                                           input_table_list_of_fields_intersect,
                                           match_table, match_table_uuid, match_table_list_of_fields_intersect):
    """Recheck duplicate matches.
    :param input_table:dataframe
    :param unique_uuid:unique id for each records from input table
    :match_result:field name tha holds match result.This column will be updated
    :param match_name_uuid: match name uuid in the input table that attached from match table
    :param input_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    :param match_table: dataframe
    :param match_table_uuid: uuid
    :param match_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    :return: dataframe
    """

    uuid_list = input_table[input_table[match_result] == "YES"][match_name_uuid].tolist()
    dup_uuid_list = [item for item, count in Counter(uuid_list).items() if count > 1]
    print(f"There are  {len(dup_uuid_list)} many to one duplicate matches")

    for i in dup_uuid_list:
        if i != " ":
            uuid_count_dict = {}
            match_table_select = match_table[match_table[match_table_uuid] == i][match_table_list_of_fields_intersect]
            from_match_table = {match_table_select.iloc[0][j] for j in match_table_list_of_fields_intersect}
            input_table_uuid = input_table[input_table[match_name_uuid] == i][unique_uuid].tolist()
            for k in input_table_uuid:
                input_table_select = input_table[input_table[unique_uuid] == k][input_table_list_of_fields_intersect]
                from_input_table = {input_table_select.iloc[0][j] for j in input_table_list_of_fields_intersect}
                intersect = from_match_table.intersection(from_input_table)
                uuid_count_dict[k] = len(intersect)
            all_values = uuid_count_dict.values()
            max_value = max(all_values)
            max_match = list(dict(filter(lambda elem: elem[1] == max_value, uuid_count_dict.items())).keys())
            if len(max_match) == 1:
                input_table_uuid2 = [z for z in input_table_uuid if z not in max_match]
                input_table.loc[input_table[unique_uuid].isin(input_table_uuid2), match_result] = "NO"


def calculate_distance_between_matches(input_table, unique_uuid, match_name_uuid, input_table_lat, input_table_long,
                                       match_table, match_table_uuid, match_table_lat, match_table_long):
    uuid_list = input_table[match_name_uuid].unique()
    for i in uuid_list:
        if i != " ":
            match_lat = match_table.loc[match_table[match_table_uuid] == i][match_table_lat].values[0]
            match_long = match_table.loc[match_table[match_table_uuid] == i][match_table_long].values[0]
            if not np.isnan(match_long):
                input_table_uuid = input_table[input_table[match_name_uuid] == i][unique_uuid].tolist()
                for uuid in input_table_uuid:
                    get_lat = input_table.loc[input_table[unique_uuid] == uuid][input_table_lat].values[0]
                    get_long = input_table.loc[input_table[unique_uuid] == uuid][input_table_long].values[0]
                    distance_km = point_pairs_dist_calculation(match_long, match_lat, get_long, get_lat)
                    input_table.loc[input_table[unique_uuid] == uuid, "dist_to_match_km"] = distance_km


def resolve_duplicates_by_best_match(input_table, matched_uuid_expand, it_uniq_id, it_match_type, it_match_score,
                                     match_result):
    """
    :param input_table: dataframe of input table
    :param matched_uuid_expand: field of the expanded uuid from match
    :param it_uniq_id: field from original file that holds the uniq identifier (OBJECTID)
    :param it_match_type: field with the type of match
    :param it_match_score: field with the match score
    :param match_result: field with the result of the match (YES or NO)
    :return: dataframe
    """

    # for troubleshooting make a copy of the match result this can be commented out later
    # input_table['orig_result'] = input_table[match_result]
    # keep only best match based on the highest match score grouped by type of fuzzy match
    input_table['max'] = input_table.groupby([matched_uuid_expand, it_match_type, match_result])[
        it_match_score].transform('max')
    input_table.loc[input_table[it_match_score] != input_table["max"], match_result] = "NO"

    # If there is a choice between partial and full match, pick full match
    # define the rank
    input_table['match_rank'] = 1
    input_table.loc[input_table[it_match_type].str.contains('identical', na=False), 'match_rank'] = 2
    input_table.loc[input_table[it_match_type].str.contains('partial', na=False), 'match_rank'] = 0

    # find and keep only best match
    input_table['max_r'] = input_table.groupby([matched_uuid_expand, match_result])["match_rank"].transform('max')
    input_table.loc[input_table["match_rank"] != input_table["max_r"], match_result] = "NO"
    # find duplicates, the first occurrence is marked as false
    input_table['was_dupe'] = input_table[it_uniq_id].duplicated()
    index_old_dupes = input_table[(input_table['was_dupe'] == True) & (input_table[match_result] == 'NO')].index
    input_table.drop(index_old_dupes, inplace=True)
    input_table.drop('was_dupe', inplace=True, axis=1)


def resolve_duplicates_by_distance_to_bndry(input_table, it_uniq_id, distance_fld, match_result):
    """
    :param input_table: dataframe of input table
    :param it_uniq_id: field from the original file that holds the uniq identifier (OGJECTID)
    :param distance_fld: field that hold the distance to the boundary
    :param match_result: field that holds the match result of YES or NO
    :return: a data frame
    """
    input_table[distance_fld].fillna('0', inplace=True)
    input_table[distance_fld].replace('-1', '0', inplace=True)
    input_table[distance_fld] = input_table[distance_fld].astype(float)
    input_table['min_dist'] = input_table.groupby([it_uniq_id, match_result])[distance_fld].transform('min')
    input_table.loc[input_table[distance_fld] != input_table['min_dist'], match_result] = "NO"


def expand_a_table(input_df, field_to_expand, how_to_split="/"):
    expand_duplicated_match = input_df[[field_to_expand]]
    expand_duplicated_match["match_uuid_expand"] = expand_duplicated_match[field_to_expand].str.split(how_to_split)
    expand_duplicated_match = expand_duplicated_match.explode("match_uuid_expand")
    expand_duplicated_match = expand_duplicated_match.drop_duplicates()
    input_df = expand_duplicated_match.merge(input_df, on=field_to_expand, how="left")
    return input_df


def transfer_columns_between_input_match_table(input_df, input_df_match_uuid, match_df, match_uuid, transfer_cols=[]):
    input_df.drop("match_uuid_expand", axis=1, inplace=True, errors="ignore")
    expand_df = expand_a_table(input_df, input_df_match_uuid, how_to_split="/")
    match_df = match_df[[match_uuid] + transfer_cols]
    match_df_columns = match_df.columns
    for i in match_df_columns:
        if i in expand_df.columns:
            match_df.rename({i: i + "_2"}, inplace=True, axis=1)
    result_df = expand_df.merge(match_df, left_on="match_uuid_expand", right_on=match_uuid, how="left")
    return result_df


def matching_rapidfuzz(match_name, match_candidates):
    name_matched, score, index = \
        rapid_process.extractOne(match_name, match_candidates, scorer=Levenshtein.normalized_similarity,
                                 processor=rapid_utils.default_process)
    score = score * 100
    if score == 100:
        return name_matched, score, "identical", "YES"

    if (len(match_name) <= 4 and score >= 70) | (len(match_name) == 5 and score >= 75) | (score >= 82):
        return name_matched, score, "levenshtein", "YES"

    name_matched, score, index = rapid_process.extractOne(match_name, match_candidates, scorer=JaroWinkler.similarity,
                                                          score_cutoff=0, processor=rapid_utils.default_process)
    score = score * 100
    if score >= 87:
        return name_matched, score, "jaro_winkler_similarity", "YES"

    name_matched, score, index = rapid_process.extractOne(match_name, match_candidates, scorer=Jaro.similarity,
                                                          score_cutoff=0, processor=rapid_utils.default_process)
    score = score * 100
    if score >= 87:
        return name_matched, score, "jaro_similarity", "YES"

    name_matched, score, index = rapid_process.extractOne(match_name, match_candidates, scorer=rapidfuzz.fuzz.ratio,
                                                          score_cutoff=0, processor=rapid_utils.default_process)
    if score >= 85:
        return name_matched, score, "fuzz_ratio", "YES"

    name_matched, score, index = rapid_process.extractOne(match_name, match_candidates, scorer=rapidfuzz.fuzz.token_ratio,
                                                          score_cutoff=0, processor=rapid_utils.default_process)
    if score >= 87:
        return name_matched, score, "token_ratio", "YES"

    get_matches = rapid_process.extract(match_name, match_candidates, scorer=rapidfuzz.fuzz.partial_ratio,
                                        score_cutoff=0, processor=rapid_utils.default_process, limit=5)
    get_matches = [name for name, score, index in get_matches if score >= 85]
    if len(get_matches) > 0:
        name_matched, score, index = rapid_process.extractOne(match_name, get_matches, scorer=rapidfuzz.fuzz.ratio,
                                                              score_cutoff=0, processor=rapid_utils.default_process)
        if score >= 50:
            return name_matched, score, "partial_ratio", "YES"

    get_matches = rapid_process.extract(match_name, match_candidates, scorer=rapidfuzz.fuzz.partial_token_ratio,
                                        score_cutoff=0, processor=rapid_utils.default_process, limit=5)
    get_matches = [name for name, score, index in get_matches if score >= 85]
    if len(get_matches) > 0:
        name_matched, score, index = rapid_process.extractOne(match_name, get_matches,
                                                              scorer=rapidfuzz.fuzz.ratio, score_cutoff=0,
                                                              processor=rapid_utils.default_process)
        if score >= 50:
            return name_matched, score, "partial_token_ratio", "YES"

    name_matched, score, index = rapid_process.extractOne(match_name, match_candidates,
                                                          scorer=Levenshtein.normalized_similarity,
                                                          processor=rapid_utils.default_process)
    return name_matched, score, "levenshtein", "NO"


def matching_fuzzywuzzy(input_name, match_candidates):
    """
    match with fuzzywuzzy package
    :param input_name: a name to be matched
    :param match_candidates: list of candidates
    :return: match name with match score
    """

    ratio_name_matched, ratio_score = wuzzy_process.extractOne(input_name, match_candidates, scorer=fuzz.ratio)
    if ratio_score == 100:
        return ratio_name_matched, ratio_score, "identical", "YES"

    if (len(input_name) <= 4 and ratio_score >= 70) or \
            (len(input_name) == 5 and ratio_score >= 75) or \
            ratio_score >= 78:
        return ratio_name_matched, ratio_score, "fuzz_ratio", "YES"

    sort_name_matched, sort_score = wuzzy_process.extractOne(input_name, match_candidates, scorer=fuzz.token_sort_ratio)
    if sort_score >= 78:
        return sort_name_matched, sort_score, "fuzz_token_ratio", "YES"

    all_matches = wuzzy_process.extractBests(input_name, match_candidates, scorer=fuzz.partial_token_set_ratio, limit=5)
    token_candidates = [name for name, score in all_matches if score >= 85]
    if len(token_candidates) > 0:
        name_matched, set_score = wuzzy_process.extractOne(input_name, token_candidates, scorer=fuzz.ratio)
        if set_score >= 50:
            return name_matched, set_score, "partial_ratio", "YES"

    return ratio_name_matched, ratio_score, "fuzz_ratio", "NO"


def fuzzy_match(input_table, match_var_raw, match_table, match_to_var_raw, mt_pio_type,
                match_level="", input_table_level_vars=None, match_table_level_vars=None, use_rapid=True):
    """
    Fuzzy match by using multiple fuzzy match methods
    :param input_table: input dataframe
    :param match_var_raw: name of field that holds names to be matched
    :param input_table_level_vars: list of fields to create match window.Names  with respective window will be matched against each other
    :param match_table: match dataframe
    :param match_to_var_raw: name of field that holds names to be matched to
    :param mt_pio_type match table type for uuid creation
    :param match_table_level_vars: list of fields to create match window.Names  with respective window will be matched against each other
    :param match_level: level of window such as admin 1 or admin2
    :param use_rapid: should we use rapidfuzzy or fuzzy_wuzzy matching
    :return: These field be added to input dataframe
        match_var+"_updated": cleaned version (check preclean method) of names that used for matching and it updated with matched name if
                                it is matched.
        match_var+"_match_name": The names that is match at highest score
        match_var+"_match_uuid": unique uuid of match name. This field can be used to join input dataframe with match dataframe
        match_var+"_match_result": Result of the match based on specified match score. YES> matched, NO> not matched
        match_var+"_match_score": match score
        match_var+"_match_type": match level and fuzzy match method
    """

    # some column names
    if input_table_level_vars is None:
        input_table_level_vars = []
    if match_table_level_vars is None:
        match_table_level_vars = []

    match_var = match_var_raw + "_cleaned"
    match_var_result = match_var_raw + "_match_result"
    match_var_updated = match_var_raw + "_updated"
    match_var_name = match_var_raw + "_match_name"
    match_var_uuid = match_var_raw + "_match_uuid"
    match_var_score = match_var_raw + "_match_score"
    match_var_type = match_var_raw + "_match_type"

    match_to_var = match_to_var_raw + "_cleaned"
    match_to_var_uuid = match_to_var_raw + "_uuid"

    # clean match names from both tables
    preclean(input_table, match_var_raw, match_var)
    preclean(match_table, match_to_var_raw, match_to_var)

    # create matching level variables
    create_unique_column(input_table, input_table_level_vars)
    create_unique_column(match_table, match_table_level_vars)

    match_levels = [""]
    match_mask = []
    input_mask = []

    # match with specified level.Only names in respective level will be matched
    if "unique_name" in match_table.columns:
        match_levels = match_table.unique_name.unique()

        # create uuid in match table
        if match_to_var_uuid not in match_table.columns:
            if mt_pio_type is not None:
                create_uuid_code(match_table, ["unique_name", mt_pio_type, match_to_var], match_to_var_uuid)
            else:
                create_uuid_code(match_table, ["unique_name", match_to_var], match_to_var_uuid)

    # otherwise match them all
    else:
        if match_to_var_uuid not in match_table.columns:
            if mt_pio_type is not None:
                create_uuid_code(match_table, [match_to_var, mt_pio_type], match_to_var_uuid)
            else:
                create_uuid_code(match_table, [match_to_var], match_to_var_uuid)

        match_mask = [True] * len(match_table)
        input_mask = [True] * len(input_table)

    if match_level != "":
        match_level = str(match_level) + "/ "

    # match with specified level.Only names in respective level will be matched
    for i in match_levels:

        # assumes either both or neither have this column
        if i != "":
            match_mask = (match_table["unique_name"] == i)
            input_mask = (input_table["unique_name"] == i)

        match_candidates = match_table[match_mask][match_to_var].unique()
        match_names = input_table[input_mask][match_var].unique()

        for match_name in match_names:
            if len(match_candidates) >= 1 and len(match_names) >= 1:

                if use_rapid:
                    name_matched, match_score, match_type, match_result = \
                        matching_rapidfuzz(match_name, match_candidates)
                else:
                    name_matched, match_score, match_type, match_result = \
                        matching_fuzzywuzzy(match_name, match_candidates)

                match_uuid = "/".join(
                    match_table[match_mask & (match_table[match_to_var] == name_matched)][match_to_var_uuid].unique())

                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_updated] = name_matched
                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_name] = name_matched
                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_uuid] = match_uuid
                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_result] = match_result
                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_score] = match_score
                input_table.loc[(input_table[match_var] == match_name) & input_mask, match_var_type] = \
                    match_level + match_type

    input_table.loc[input_table[match_var_result] == "NO", match_var_updated] = input_table[match_var]
    input_table.drop(["unique_name", match_var, "unique_name"], axis=1, inplace=True, errors="ignore")
    match_table.drop("unique_name", axis=1, inplace=True, errors="ignore")

    # get match result
    match_count1 = len(input_table[input_table[match_var_result] == "YES"][match_var_updated].unique())
    match_count2 = len(input_table[input_table[match_var_result] == "NO"][match_var_updated].unique())
    print(f" >>> {match_count1} Poi name matched between input data and match table")
    print(f" >>> {match_count2} Poi name did not matched between input data and match table")
    print("New Input table size:", str(len(input_table)))


def fuzzy_match_within_distance(input_table, id_field, match_var_raw, match_table, match_to_var_raw,
                                 fields_to_create_uuid=[], match_distance_m=250, use_rapid=False):
    """
    matching names from spatial layers with specified distance
    :param input_table: dataframe
    :param id_field id to identify unique row from input table
    :param match_var_raw: field name that holds names to matched
    :param match_table: dataframe
    :param match_to_var_raw:field name that holds names to matched to
    :param fields_to_create_uuid: list of field from match table to create uuid
    :param match_distance_m: distance in meter
    :param use_rapid: should we use rapid or fuzzywuzzy
    :return: input table with these added fields:
        match_var+"_updated": cleaned version (check preclean method) of names that used for matching and it
            updated with matched name ifit is matched.
        match_var+"_match_name": The names that is match at specified threshold
        match_var+"_match_uuid": unique uuid of match name. This field can be used to join input and match tables
        match_var+"_match_result": Result of the match based on specified match score. YES> matched, NO> not matched
        match_var+"_match_score": match score
        match_var+"_match_type": match level and fuzzy match method
    """

    # make an index column
    input_table.drop("index", inplace=True, axis=1, errors="ignore")
    input_table.reset_index(inplace=True)

    # some column names
    match_var = match_var_raw + "_cleaned"
    match_var_result = match_var_raw + "_match_result"
    match_var_updated = match_var_raw + "_updated"
    match_var_uuid = match_var_raw + "_match_uuid"
    match_var_score = match_var_raw + "_match_score"
    match_var_name = match_var_raw + "_match_name"
    match_var_type = match_var_raw + "_match_type"

    match_to_var = match_to_var_raw + "_cleaned"
    match_to_var_uuid = match_to_var_raw + "_uuid"

    # clean match_var and match_to_var columns from both table
    preclean(input_table, match_var_raw, match_var)
    preclean(match_table, match_to_var_raw, match_to_var)

    # create uuid in match table
    if match_to_var_uuid not in match_table.columns:
        create_uuid_code(match_table, fields_to_create_uuid, match_to_var_uuid)

    # make spatial join based on specified distance
    input_table_proj = input_table.to_crs("ESRI:54032")
    match_table_proj = match_table.to_crs("ESRI:54032")
    match_table_proj['geometry'] = match_table_proj.geometry.buffer(match_distance_m)
    input_table_proj = input_table_proj.sjoin(
        match_table_proj[[match_to_var, match_to_var_uuid, "geometry"]], how="left")
    input_table_match = input_table_proj.to_crs("EPSG:4326")
    input_table_match[match_to_var].fillna("", inplace=True)
    input_table_match.reset_index(drop=True, inplace=True)

    # spatial join may result in one to many join meaning that more than one point
    # from match table can fall in to specified region.
    # process below finds the best match

    input_table_group = input_table_match.groupby(id_field)
    for i, df_group in input_table_group:
        match_name = df_group[match_var].tolist()[0]
        match_candidates = [s for s in df_group[match_to_var].tolist() if s != '']
        if len(match_candidates) > 0:

            if use_rapid:
                name_matched, match_score, match_type, match_result = \
                    matching_rapidfuzz(match_name, match_candidates)
            else:
                name_matched, match_score, match_type, match_result = \
                    matching_fuzzywuzzy(match_name, match_candidates)

            match_uuid = "/".join(df_group[df_group[match_to_var] == name_matched][match_to_var_uuid].unique())

            input_table_match.loc[input_table_match.index.isin(df_group.index), match_var_updated] = name_matched
            input_table_match.loc[
                input_table_match.index.isin(df_group.index), match_var_name] = name_matched
            input_table_match.loc[input_table_match.index.isin(df_group.index), match_var_uuid] = match_uuid
            input_table_match.loc[input_table_match.index.isin(df_group.index), match_var_result] = match_result
            input_table_match.loc[input_table_match.index.isin(df_group.index), match_var_score] = match_score
            input_table_match.loc[input_table_match.index.isin(df_group.index), match_var_type] = \
                "{x} in {y} distance".format(y=match_distance_m, x=match_type)

    # drop duplicate match because spatial join may cause one to many join
    # match with the highest score will be kept

    input_table_match[match_var_result].fillna("NO", inplace=True)
    input_table_match.drop_duplicates(subset=[id_field], keep="last", inplace=True)

    # get match result
    match_count1 = len(input_table_match[input_table_match[match_var_result] == "YES"][match_var_raw].unique())
    match_count2 = len(input_table_match[input_table_match[match_var_result] == "NO"][match_var_raw].unique())
    print(f" >>> {match_count1} Poi name matched between input data and match table")
    print(f" >>> {match_count2} Poi name did not matched between input data and match table")

    return input_table_match


def resolve_dup_match_by_attribute(input_table, id_field, match_name_uuid, expand_match_name_uuid, match_result,
                                   input_table_list_of_fields_intersect, match_table, match_table_uuid,
                                   match_table_list_of_fields_intersect):
    """Reevalates duplicate matches.
    :param input_table:dataframe
    :param id_field:unique identification for each entity in input table
    :param expand_match_name_uuid: match name uuid in the input table that attached from match table
    :param match_result:
    :param input_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    :param match_table: dataframe
    :param match_table_uuid: uuid
    :param match_table_list_of_fields_intersect: List fields to resolve duplicate matches.For example admin and match name
    """
    input_table[expand_match_name_uuid].fillna(" ", inplace=True)

    # Process 1: resolve one to many duplicate match by attribute ####
    id_list = input_table[input_table[match_result] == "YES"][id_field].tolist()
    dup_id_list = [item for item, count in Counter(id_list).items() if count > 1]

    print(f"There are  {len(dup_id_list)} names from input table matched to more than one name from match table!")
    if len(dup_id_list) > 0:
        for i in dup_id_list:
            uuid_count_dict = {}
            input_table_select = input_table[input_table[id_field] == i][input_table_list_of_fields_intersect]
            from_input_table = {input_table_select.iloc[0][j] for j in input_table_list_of_fields_intersect}
            match_name_uuids = input_table[input_table[id_field] == i][expand_match_name_uuid].tolist()
            for k in match_name_uuids:
                match_table_select = match_table[match_table[match_table_uuid] == k][match_table_list_of_fields_intersect]
                from_match_table = {match_table_select.iloc[0][j] for j in match_table_list_of_fields_intersect}
                intersect = from_input_table.intersection(from_match_table)
                uuid_count_dict[k] = len(intersect)
            all_values = uuid_count_dict.values()
            max_value = max(all_values)
            max_match = list(dict(filter(lambda elem: elem[1] == max_value, uuid_count_dict.items())).keys())
            input_table.loc[(input_table[id_field] == i) & (~input_table[expand_match_name_uuid].isin(max_match)),
                            match_result] = "delete"
            # if we removed some, we'll want to update the rest with what's remaining
            max_match_combine = "/".join(max_match)
            input_table.loc[(input_table[id_field] == i) & (input_table[expand_match_name_uuid].isin(max_match)),
                            match_name_uuid] = max_match_combine

        resolve_count = input_table[input_table[match_result] == "delete"].shape[0]
        print(f"{resolve_count} duplicate matched names were fixed by attribute!")
        input_table.drop(input_table[input_table[match_result] == "delete"].index, inplace=True)
        input_table.reset_index(drop=True, inplace=True)

    # Process 2: resolve many to one duplicate match by attribute ####
    match_name_uuid_list = input_table[input_table[match_result] == "YES"][expand_match_name_uuid].tolist()
    dup_match_name_uuid_list = [item for item, count in Counter(match_name_uuid_list).items() if count > 1]
    dup_match_name_uuid_list = [l for l in dup_match_name_uuid_list if l !=" "]

    print(f"There are  {len(dup_match_name_uuid_list)} names from match table matched to more than a name from input table!")
    if len(dup_match_name_uuid_list) > 0:
        for i in dup_match_name_uuid_list:
            uuid_count_dict = {}
            match_table_select = match_table[match_table[match_table_uuid] == i][match_table_list_of_fields_intersect]
            from_match_table = {match_table_select.iloc[0][j] for j in match_table_list_of_fields_intersect}
            input_table_uuid = input_table[input_table[expand_match_name_uuid] == i][id_field].tolist()
            for k in input_table_uuid:
                input_table_select = input_table[input_table[id_field] == k][input_table_list_of_fields_intersect]
                from_input_table = {input_table_select.iloc[0][j] for j in input_table_list_of_fields_intersect}
                intersect = from_match_table.intersection(from_input_table)
                uuid_count_dict[k] = len(intersect)
            all_values = uuid_count_dict.values()
            max_value = max(all_values)
            max_match = list(dict(filter(lambda elem: elem[1] == max_value, uuid_count_dict.items())).keys())

            if len(max_match) == 1:
                input_table_uuid2 = [z for z in input_table_uuid if z not in max_match]
                input_table.loc[input_table[id_field].isin(input_table_uuid2), match_result] = "NO"

            #input_table.loc[(input_table[match_name_uuid]==i)&(~input_table[id_field].isin(max_match)), match_result] = "NO"

        match_name_uuid_list = input_table[input_table[match_result] == "YES"][expand_match_name_uuid].tolist()
        dup_match_name_uuid_list_ = [item for item, count in Counter(match_name_uuid_list).items() if count > 1]
        num_fixed = len(dup_match_name_uuid_list)-len(dup_match_name_uuid_list_)
        print(f"{num_fixed} duplicate matched names were fixed by attribute!")


def resolve_dup_match_by_distance(input_table, id_field, match_name_uuid, match_result, input_table_lat,
                                  input_table_long, match_table, match_table_uuid, match_table_lat, match_table_long,
                                  distance_m=500):
    """
    :param input_table: geodataframe
    :param id_field:unique identification for each entity in input table
    :param match_name_uuid: match name unique uuid from match table
    :param match_result: yes/no
    :param input_table_lat: latitude
    :param input_table_long: longitude
    :param match_table: geodataframe
    :param match_table_uuid: match name unique uuid from match table
    :param match_table_lat: latitude
    :param match_table_long: longitude
    :param distance_m: distance to check within (in meters)
    """

    #### Process 1: resolve one to many duplicate match by distance ####
    id_list = input_table[(input_table[match_result] == "YES") & (input_table[input_table_lat].notnull())][id_field].tolist()
    dup_id_list = [item for item, count in Counter(id_list).items() if count > 1]
    print(f"There are  {len(dup_id_list)} names from input table matched to more than a name from match table!")
    if len(dup_id_list) > 0:
        for i in dup_id_list:
            dist_dict = {}
            get_visit_lat = input_table.loc[input_table[id_field] == i][input_table_lat].values[0]
            get_visit_long = input_table.loc[input_table[id_field] == i][input_table_long].values[0]
            match_name_uuids = input_table[input_table[id_field] == i][match_name_uuid].tolist()
            for k in match_name_uuids:
                get_mfl_lat = match_table.loc[match_table[match_table_uuid] == k][match_table_lat].values[0]
                get_mfl_long = match_table.loc[match_table[match_table_uuid] == k][match_table_long].values[0]
                distance = point_pairs_dist_calculation(get_visit_long, get_visit_lat, get_mfl_long, get_mfl_lat)
                dist_dict[k] = distance
            closest_uuid = min(dist_dict, key=dist_dict.get)
            if dist_dict[closest_uuid] <= distance_m:
                input_table.loc[(input_table[id_field] == i)&
                                (input_table[match_name_uuid] != closest_uuid), match_result] = "delete"

        resolve_count = input_table[input_table[match_result] == "delete"].shape[0]
        print(f"{resolve_count} duplicate matched names were fixed by distance!")
        input_table.drop(input_table[input_table[match_result] == "delete"].index, inplace=True)
        input_table.reset_index(drop=True, inplace=True)

    #### Process 2: resolve many to one duplicate match by distance ####
    match_name_uuid_list = input_table[(input_table[match_result] == "YES")&
                                        (input_table[input_table_lat].notnull())][match_name_uuid].tolist()
    dup_match_name_uuid_list = [item for item, count in Counter(match_name_uuid_list).items() if count > 1]
    print(f"There are {len(dup_match_name_uuid_list)} names from match table matched to more than a name from input table!")
    if len(dup_match_name_uuid_list )>1:
        for i in dup_match_name_uuid_list:
            dist_dict = {}
            match_lat = match_table.loc[match_table[match_table_uuid] == i][match_table_lat].values[0]
            match_long = match_table.loc[match_table[match_table_uuid] == i][match_table_long].values[0]
            input_table_uuid = input_table[input_table[match_name_uuid] == i][id_field].tolist()
            for k in input_table_uuid:
                target_row = input_table.loc[input_table[id_field] == k]
                get_lat = target_row[input_table_lat].values[0]
                get_long = target_row[input_table_long].values[0]
                # get_long = input_table.loc[input_table[k] == uuid][input_table_long].values[0]
                p_distance = point_pairs_dist_calculation(match_long, match_lat, get_long, get_lat)
                dist_dict[uuid] = p_distance
            closest_uuid = min(dist_dict, key=dist_dict.get)
            if dist_dict[closest_uuid] <= distance_m:
                input_table.loc[(input_table[match_name_uuid]==i)&(input_table[id_field]!=closest_uuid),
                                match_result] = "NO"
        match_name_uuid_list = input_table[(input_table[match_result] == "YES") &
                                           (input_table[input_table_lat].notnull())][match_name_uuid].tolist()
        dup_match_name_uuid_list_ = [item for item, count in Counter(match_name_uuid_list).items() if count > 1]
        num_fixed = len(dup_match_name_uuid_list) - len(dup_match_name_uuid_list_)
        print(f"{num_fixed} duplicate matched names were fixed by distance!")

