import os
import pandas as pd
import geopandas
import unidecode
import re
import numpy as np
from ordered_set import OrderedSet
from sklearn.cluster import DBSCAN
from argparse import ArgumentParser
from datetime import date

from rapidfuzz import process as rapid_process
from rapidfuzz import utils as rapid_utils
from fuzzywuzzy import process as wuzzy_process
from fuzzywuzzy import fuzz
from collections import Counter
from scipy.spatial import distance
import uuid
import sys


def abort(reason):
    print(reason)
    sys.exit(-1)


def is_interactive():
    import __main__ as main
    return not hasattr(main, '__file__')


def check_config_override(default_config_file):
    # default config file
    config_file = default_config_file

    if not is_interactive():
        # load command line arguments
        parser = ArgumentParser()
        parser.add_argument("-c", "--config", dest="config_filename",
                            help="specify a config file to use", metavar="FILE")

        args = parser.parse_args()

        # override config file if it is specified
        if args.config_filename:
            config_file = args.config_filename

    if not os.path.isfile(config_file):
        abort("Can't find the specified config file - '" + config_file)

    return config_file


def sanity_check_df(df, src, column_list):

    for cn in column_list:
        if not cn == "" and cn not in df.columns:
            abort("missing field '" + cn + "' from " + src)


def get_file_type(file_path):
    """
    :param file_path: full file path
    :return: file type
    """

    basename = os.path.basename(file_path)
    dirname = os.path.dirname(file_path)

    if basename.endswith(".csv"):
        return "csv"
    elif basename.endswith(".xlsx") | basename.endswith(".xls"):
        return "xlsx"
    elif basename.endswith(".shp"):
        return "shp"
    elif basename.endswith(".gpkg"):
        return "gpkg"
    elif ".gdb" in dirname:
        return "feature"
    else:
        return "unknown"


def clean_geom(input_filename, result, geom):
    if result is None:
        print("unable to load into df?")
        exit()

    if geom not in result.columns:
        print("missing field " + geom)

    # replace any value with the string "null" in it with nan
    result[geom].replace(r'(?i).*null.*', np.nan, inplace=True, regex=True)

    # replace empty (or just whitespace) values with nan
    result[geom].replace(r'^\s*$', np.nan, inplace=True, regex=True)

    non_num = (result[geom].apply(lambda x: not isinstance(x, float))).to_list()

    if any(non_num):
        first_bad_loc = non_num.index(True)
        print("In file '" + input_filename + "' there are " + str(sum(non_num)) + " non-numbers in column '" + geom +
              "', the first example is '" + result[geom][first_bad_loc] + "' at row " + str(first_bad_loc))
        exit()

    result[geom] = result[geom].astype(float)


def read_data(input_filename, lat="lat", long="long", null_val=r'<NULL>', strip_headers=True):
    """
    read data in shp, csv, or xlsx
    :param input_filename: input file to load in
    :param lat: column name for latitude values
    :param long: column name for longitude values
    :param null_val: value to replace with nan's
    :param strip_headers: strip the column headers of pre/post whitespace
    :returns: resulting dataframe
    """

    file_format = get_file_type(input_filename)

    if file_format == "shp":
        result = geopandas.read_file(input_filename)
    elif file_format == "feature":
        # Read file from File Geodatabase
        head_tail = os.path.split(input_filename)
        file_only = head_tail[1]
        path_only = head_tail[0]
        result = geopandas.read_file(path_only, driver="FileGDB", layer=file_only)
    elif file_format == "csv":
        try:
            result = pd.read_csv(input_filename)
        except:
            result = pd.read_csv(input_filename, encoding="ISO-8859-1")
        if lat in result.columns:
            clean_geom(input_filename, result, long)
            clean_geom(input_filename, result, lat)
            result = geopandas.GeoDataFrame(result, geometry=geopandas.points_from_xy(result[long], result[lat]),
                                            crs="EPSG:4326")
    elif file_format == "xlsx":
        result = pd.DataFrame()
        tmp_df = pd.read_excel(input_filename, None)
        for i in tmp_df.keys():
            result = pd.concat([result, tmp_df[i]])

        result.reset_index(inplace=True, drop=True)

        if lat in result.columns:
            clean_geom(input_filename, result, long)
            clean_geom(input_filename, result, lat)
            result = geopandas.GeoDataFrame(result, geometry=geopandas.points_from_xy(result[long], result[lat]),
                                            crs="EPSG:4326")
    elif file_format == "gpkg":
        result = geopandas.read_file(input_filename, driver="GPKG")

    else:
        print("Error: can't load file '" + input_filename + "' with type '" + str(file_format) + "'")
        result = None
        exit(-1)

    try:
        if null_val is not None and file_format != "feature":  # can't do this with ArcPy dataframes
            result.replace(null_val, np.nan, inplace=True)
    except:
        print("wasn't able to remove nulls")

    if strip_headers:
        result.rename(str.strip, axis='columns', inplace=True)

    return result


def write_data(df, out_filename):
    """
    write data in feature, shp, csv, or xlsx
    :param df: dataframe
    :param out_filename: file to write file to.
    :returns: filename we actually wrote
    """

    file_format = get_file_type(out_filename)

    if file_format == "shp" and "SHAPE" in df.columns:
        df.spatial.to_featureclass(out_filename)
    elif file_format == "shp" and "SHAPE" not in df.columns:
        if isinstance(df, geopandas.GeoDataFrame):
            stringcols = df.select_dtypes(include='datetime64').columns
            df[stringcols] = df[stringcols].fillna('').astype(str)
            df.to_file(out_filename)
        else:
            out_filename = os.path.splitext(out_filename)[0] + ".xlsx"
            # strip the base file name out to label the sheet, excel limit is 31 characters
            basename = os.path.splitext(os.path.basename(out_filename))[0][0:31]
            df.to_excel(out_filename, sheet_name=basename, index=False)
    elif file_format == "xlsx":
        if any(x in df.columns for x in ["geometry", "SHAPE"]):
            df = df.drop(["geometry", "SHAPE"], axis=1, errors="ignore")
        # strip the base file name out to label the sheet, excel limit is 31 characters
        basename = os.path.splitext(os.path.basename(out_filename))[0][0:31]
        df.to_excel(out_filename, sheet_name=basename, index=False)
    elif file_format == "csv":
        if any(x in df.columns for x in ["geometry", "SHAPE"]):
            df = df.drop(["geometry", "SHAPE"], axis=1, errors="ignore")
        df.to_csv(out_filename, index=False)  # , encoding="latin-1")
    elif file_format == "gpkg":
        if isinstance(df, geopandas.GeoDataFrame):
            # convert all "objects" to strings, gpkg doesn't like mixed columns
            stringcols = df.select_dtypes(include='object').columns
            df[stringcols] = df[stringcols].fillna('').astype(str)
            df.to_file(out_filename, driver="GPKG")
        else:
            out_filename = os.path.splitext(out_filename)[0] + ".xlsx"
            # strip the base file name out to label the sheet, excel limit is 31 characters
            basename = os.path.splitext(os.path.basename(out_filename))[0][0:31]
            df.to_excel(out_filename, sheet_name=basename, index=False)
    elif file_format == "feature":
        if "SHAPE" in df.columns:
            df.spatial.to_featureclass(out_filename)
        elif isinstance(df, geopandas.GeoDataFrame):
            from arcgis.features import GeoAccessor
            sdf = GeoAccessor.from_geodataframe(df, column_name="geometry")
            sdf.spatial.to_featureclass(out_filename)
        else:
            print("Can't save a feature class without a geometry or SHAPE")
    else:
        print("couldn't figure out how to save file type: " + str(file_format))
        return ""

    return out_filename


def preclean(df, input_variable, output_variable, remove_accent=True):
    """
    Basic cleaning and standardization of a column
    :param df: dataframe
    :param input_variable: a column name to be cleaned/standardized
    :param output_variable: cleaned/standardized column name
    :param remove_accent:remove french characters
    :return: cleaned dataframe
    """
    # geopandas version spams with false positives so turn it off
    pd.set_option('mode.chained_assignment', None)

    # replace NAs with empty string '' and assign to our new field
    df[output_variable] = df[input_variable].fillna('')

    # remove accent marks
    if remove_accent:
        df[output_variable] = [unidecode.unidecode(str(n)) for n in df[output_variable]]

    # convert ampersands
    df[output_variable].replace('&', 'and', inplace=True)

    # make everthing title case, we were doing this before, moved up to make regex easier
    df[output_variable] = df[output_variable].str.title()

    # replace "And" to and
    df[output_variable].replace(r" And\b", " and", inplace=True, regex=True)

    # replace `S to `s
    df[output_variable].replace(r"`S\b", " `s", inplace=True, regex=True)

    # convert Roman numerals
    df[output_variable].replace(r" Iii\b", " 3", inplace=True, regex=True)
    df[output_variable].replace(r" Ii\b", " 2", inplace=True, regex=True)
    df[output_variable].replace(r" I\b", " 1", inplace=True, regex=True)
    df[output_variable].replace(r" Iv\b", " 4", inplace=True, regex=True)
    df[output_variable].replace(r" V\b", " 5", inplace=True, regex=True)

    # split up any words with numbers in them (i.e. Heart1Hosp becomes Heart 1 Hosp)
    df[output_variable] = df[output_variable].apply(lambda x: " ".join(re.split('(\d+)', x)))

    # replace everything that's not a number or a digit with a space
    df[output_variable] = df[output_variable].map(lambda x: re.sub(r"\.", '', x))

    # replace everything that's not a number or a digit , or - with a space
    df[output_variable] = df[output_variable].map(lambda x: re.sub(r"[^a-zA-Z0-9()']", ' ', x))

    # splitting and replacing can result in blocks of several spaces, reduce them to 1
    df[output_variable].replace(r'\s+', ' ', inplace=True, regex=True)

    # strip any preceding/trailing space, not using strip to avoid the copy
    df[output_variable].replace(" $", "", inplace=True, regex=True)
    df[output_variable].replace("^ ", "", inplace=True, regex=True)


def correct_spelling(df, spelling_dict, clean_name_col, output_col):
    """
    Makes correction to possible misspellings using the spelling dictionary,
    updates existing dataframe with new column
    :param df: dataframe
    :param spelling_dict: python dictionary of words to misspellings
    :param clean_name_col: cleaned/standardized column name
    :param output_col: A column name to hold corrected names
    """

    # copy our column over to work on
    df[output_col] = df[clean_name_col]

    # replace any of our misspellings
    for word in spelling_dict.keys():
        df[output_col].replace(r'(?i)(\b)' + r"(\b)|(\b)".join(spelling_dict[word]) + r'(\b)', r'\1' + word + r'\2',
                               inplace=True, regex=True)

    # not sure why this is in spelling but ok
    df[output_col].replace(" De ", " de ", inplace=True)

    # shouldn't need this anymore since we preserve boundary in regex
    # df[output_col] = df[output_col].str.strip()
    # df.reset_index(inplace=True, drop=True)


def get_type_keywords(type_dict_df):
    """
    Use facility type and abbreviations to correct and name reversals and spaces in abbreviations
    :param type_dict_df: Country specific type dictionary as a df
    :returns: reverse sorted list of all the keywords from the type column
    """

    # Get the types and create a list that includes all types and their subsets
    types = list(type_dict_df['type'])
    type_keywords = set()
    for t in types:
        # add the full facility type
        t = t.title()
        type_keywords.add(t)

        # add individual words as well
        t = t.replace('/', ' ')
        words = t.split(' ')
        # skip words that have punctuation / numbers and have length <= 3 (e.g. de, "(major)")
        words = [w for w in words if w.isalpha() and len(w) > 3]
        for w in words:
            type_keywords.add(w)

    # obtain the list of type keywords and sort in descending length
    return sorted(list(type_keywords), key=len, reverse=True)


def clean_type_info(df, type_dict_df, clean_name_col):
    """
        Use facility type and abbreviations to correct and name reversals and spaces in abbreviations
        :param df: dataframe to be updated
        :param type_dict_df: Country specific type dictionary as csv file
        :param clean_name_col: Cleaned/standardized name column to update
        """

    # strip any spaces in instances where our clean_name starts or ends with 2 or 3 letter abbreviations
    # e.g. "C S BLAH" to "CS BLAH" in the clean_name column
    abbrevs = set(type_dict_df['abbreviation'])
    tmp_types = [t for t in abbrevs if (len(t) <= 3)]
    tmp_types = sorted(tmp_types, key=len, reverse=True)
    for t in tmp_types:
        df[clean_name_col].replace('(?i)^' + ' '.join(list(t)) + ' ', t + ' ', regex=True, inplace=True)
        df[clean_name_col].replace('(?i) ' + ' '.join(list(t)) + '$', ' ' + t, regex=True, inplace=True)

    # handle situations when type is 'Hospital District' in the type dictionary
    # but name column has 'District Hospital' in ISS data
    type_keywords = get_type_keywords(type_dict_df)
    type_len_2 = [t for t in type_keywords if len(t.split()) == 2]
    for t in type_len_2:
        df[clean_name_col].replace('(?i)' + ' '.join(t.split()[::-1]), t, inplace=True, regex=True)



def remove_type_info(df, type_dict_df, clean_name_col, clean_name_final_col):
    """
    Use facility type and abbreviations in the type dictionary as keywords and remove type information
    :param df: dataframe to be updated
    :param type_dict_df: Country specific type dictionary as csv file
    :param clean_name_col: Cleaned/standardized name column
    :param clean_name_final_col: Output column to keep name without a type
    """

    # abbreviations for that country
    abbrevs = set(type_dict_df['abbreviation'])

    # create a sorted list of title case whole word filters for our abbreviations
    # e.g. for CS, 4 patterns are considered: '^Cs ', ' Cs ', ' Cs$', '^Cs$'
    abb_keywords = []
    for abbrev in abbrevs:
        abb_keywords.append(r'\b' + abbrev.title() + r'\b')

    abb_keywords = sorted(abb_keywords, key=len, reverse=True)

    # get a sorted list of our possible types
    type_keywords = get_type_keywords(type_dict_df)

    # assigning to our new column, making sure it is in title case
    df[clean_name_final_col] = df[clean_name_col].str.title()

    # remove type information using keywords generated above
    df[clean_name_final_col].replace('|'.join(type_keywords), '', inplace=True, regex=True)
    df[clean_name_final_col].replace('|'.join(abb_keywords), ' ', inplace=True, regex=True)

    # remove meaningless connecting words like de, do, da, du
    df[clean_name_final_col].replace(r'\bDe\b|\bDo\b|\bDa\b|\bDu\b|^Dos|^Das', ' ', regex=True, inplace=True)
    df[clean_name_final_col].replace(r'\s+', ' ', inplace=True, regex=True)

    # strip any preceding/trailing space, not using strip to avoid the copy
    df[clean_name_final_col].replace(" $", "", inplace=True, regex=True)
    df[clean_name_final_col].replace("^ ", "", inplace=True, regex=True)


def extract_type(df, clean_name_col, clean_name_final_col, extract_type_col):
    """
    Removes the type of facility from a facility name, and puts the type into a separate column
        exp: "Kayamba Centre de Sante" >> "Kayamba"  ||  "Centre de Sante"
    :param df: dataframe to be updated
    :param clean_name_col: cleaned/standardized column name
    :param clean_name_final_col: A column name that holds only name(no type)
    :param extract_type_col: A column name that holds only type
    :return: dataframe
    """

    extract_types = []
    df[clean_name_col].fillna("", inplace=True)
    df[clean_name_final_col].fillna("", inplace=True)

    for idx, row in df.iterrows():
        name = row[clean_name_col].upper()
        name_final = row[clean_name_final_col].upper()

        # if clean_name_final is exactly the same as clean_name,
        # this indicates no type information can be extracted, thus append NA
        if name == name_final:
            extract_types.append(np.nan)

        else:
            name = OrderedSet(name.split())
            name_final = OrderedSet(name_final.split())
            # find the difference between two names
            diff = ' '.join(list(name.difference(name_final)))
            extract_types.append(diff.strip())

    # remove de, do, da, du at start or end of extract_type
    # replace empty string with NA
    df[extract_type_col] = extract_types
    # clean up spaces
    df[extract_type_col].replace(r'\s+', ' ', inplace=True, regex=True)
    df[extract_type_col].replace(" $", "", inplace=True, regex=True)
    df[extract_type_col].replace("^ ", "", inplace=True, regex=True)
    df[extract_type_col].replace('(?i)^de |^do |^da |^du | du$| de$| do$| da$|^de$|^do$|^da$|^du$', '',
                                 inplace=True, regex=True)
    df[extract_type_col] = df[extract_type_col].str.title()

    # replace empty string with NA
    df[extract_type_col].replace('', np.nan, inplace=True, regex=False)
    df[clean_name_col].replace('', np.nan, inplace=True, regex=False)
    df[clean_name_final_col].replace('', np.nan, inplace=True, regex=False)


def map_type(df, extract_type, sub_type, score, type_dict_df):
    """
    Use extract_type to map the type information extracted to one of the types in the type dictionary
    :param df: dataframe to be updated
    :param extract_type: Column that holds type extracted from name
    :param sub_type: A column name to hold type
    :param score: A column name to hold match score between extracted type and type dictionary
    :param type_dict_df: A dataframe with country specific type dictionary
    """

    abbrevs = list(type_dict_df['abbreviation'])
    types = list(type_dict_df['type'])
    types_abbrevs = abbrevs + types
    type_lookup = dict(zip(abbrevs, types))

    sub_types = []
    scores = []

    for idx, row in df.iterrows():

        # if extract_type is NA, just append NA
        if not isinstance(row[extract_type], str):
            sub_types.append(np.nan)
            scores.append(np.nan)

        # find best match
        else:
            match, match_score = wuzzy_process.extractOne(row[extract_type], types_abbrevs, scorer=fuzz.ratio)
            scores.append(match_score)
            # if best match is abbreviation, map it to the corresponding type
            if match in list(abbrevs):
                match_type = type_lookup[match]
                sub_types.append(match_type)
            else:
                sub_types.append(match)
    df[sub_type] = sub_types
    df[score] = scores


def facility_sanity_checks(df, facility_name_clean, facility_type_clean):
    """
    add four new column to input df to keep lenght of facility name, lenght of the type, if
    facility name includes any special characters, and facility name with only numeric characters
    :param df:
    hf_name_lenght: lenght of facility name, Too long (30>) and short (<3) name needs a closer look
    hf_type_lenght: lenght of facility name, Too long (30>) and short (<3) name needs a closer look
    has_special_chrs: list of the special character a facility name has
    only_numeric: facilities with only numerical values
    """

    df["name_length"] = ""
    df["type_length"] = ""
    df["special_chars"] = ""
    df["only_numeric"] = ""

    df[facility_name_clean].fillna("", inplace=True)
    df[facility_type_clean].fillna("", inplace=True)

    check_list = ["?", "!", "//", "\\", "*", "!", "~", ")", "(", "&", "$", "+", "^", "%", "√¥", "√à", "`",
                  "√ßo", "√®", "√©"]

    for index, row in df.iterrows():
        df.loc[index, "name_length"] = len(row[facility_name_clean])
        df.loc[index, "type_length"] = len(row[facility_type_clean])

        for i in check_list:
            if i in row[facility_name_clean]:
                df.loc[index, "special_chars"] = row["special_chars"] + i

        if row[facility_name_clean].isnumeric():
            df.loc[index, "only_numeric"] = "all_numerical"


def create_geo_cluster_column(df, long, lat, radius, min_samples=2):
    """
    Cluster points based on specified distance
    :param df: dataframe
    :param long: longitude column name
    :param lat: latitude column name
    :param radius: distance in meters
    :param min_samples: minimum points
    :return: dataframe
    """

    spatial_cluster_id_column = 'geo_dbscan_r' + str(radius) + '_cluster_id'

    df["coord"] = df[[long, lat]].apply(tuple, axis=1)
    # create cluster and asing labels to points with the same cluster
    clusterer = DBSCAN(eps=(radius / 1000) / 6371., algorithm='ball_tree', metric='haversine', min_samples=min_samples)
    coorindates_array = np.array(df["coord"].apply(lambda tup: np.radians(np.array(tup))).tolist())
    clusterer.fit(coorindates_array)
    labels = clusterer.labels_

    # attached labels to points, - value indicates singlton points
    singleton_count = sum([x == -1 for x in labels])
    df[spatial_cluster_id_column] = labels
    df.loc[df[spatial_cluster_id_column] == -1, spatial_cluster_id_column] = \
        sorted(list(range(-singleton_count, 0, 1)), reverse=True)
    df.loc[df[spatial_cluster_id_column] >= 0, spatial_cluster_id_column] = \
        df.loc[df[spatial_cluster_id_column] >= 0, spatial_cluster_id_column] + 1
    df.drop("coord", inplace=True, axis=1, errors="ignore")
    return df


def check_by_admin(gdf, admin_var_from_gdf, admin_bdry_layer_gdf, admin_var_from_admin_bdry):
    """
    Check a point admin name respective to admin boundary
    :param gdf: point layer geopandas dataframe
    :param admin_var_from_gdf: admin name column from point layer
    :param admin_bdry_layer_gdf: boundary later as geopandas dataframe
    :param admin_var_from_admin_bdry: admin name column from boundary layer
    :return: point layer geopandas dataframe
    """

    if admin_var_from_gdf == admin_var_from_admin_bdry:
        admin_bdry_layer_gdf.rename(columns={admin_var_from_admin_bdry: admin_var_from_admin_bdry + "_bry"},
                                    inplace=True)
        admin_var_from_admin_bdry = admin_var_from_admin_bdry + "_bry"
    gdf_proj = gdf.to_crs("ESRI:102023")
    admin_bdry_layer_gdf_proj = admin_bdry_layer_gdf.to_crs("ESRI:102023")
    # get nearest feature

    near_join_gdf = geopandas.sjoin_nearest(gdf_proj,
                                            admin_bdry_layer_gdf_proj[[admin_var_from_admin_bdry, "geometry"]],
                                            max_distance=250, distance_col="dist_to_" + admin_var_from_admin_bdry,
                                            how="left")
    near_join_gdf = near_join_gdf[~near_join_gdf.index.duplicated(keep='first')]
    # # clean admin name from boundary
    preclean(near_join_gdf, admin_var_from_admin_bdry, admin_var_from_admin_bdry + "_clean")
    # replace na values with empty string
    near_join_gdf[admin_var_from_admin_bdry + "_clean"].fillna("", inplace=True)
    near_join_gdf[admin_var_from_gdf].fillna("", inplace=True)
    # fuzzy match
    for index, row in near_join_gdf.iterrows():
        score1 = fuzz.ratio(row[admin_var_from_gdf], row[admin_var_from_admin_bdry + "_clean"])
        score2 = fuzz.token_set_ratio(row[admin_var_from_gdf], row[admin_var_from_admin_bdry + "_clean"])

        if score1 >= 75:
            near_join_gdf.loc[index, admin_var_from_admin_bdry + "Match"] = "YES"
        elif score1 < 75 and score2 >= 98:
            near_join_gdf.loc[index, admin_var_from_admin_bdry + "Match"] = "YES"
        else:
            near_join_gdf.loc[index, admin_var_from_admin_bdry + "Match"] = "NO"

    # replace empty string with na values
    near_join_gdf.drop(['index_right', admin_var_from_admin_bdry], axis=1, inplace=True, errors="ignore")
    near_join_gdf[admin_var_from_admin_bdry + "_clean"].replace(to_replace='', value=np.nan, inplace=True)
    near_join_gdf[admin_var_from_gdf].replace(to_replace='', value=np.nan, inplace=True)
    near_join_gdf_ = near_join_gdf.to_crs("EPSG:4326")
    near_join_gdf_ = near_join_gdf_[~near_join_gdf_.index.duplicated(keep='first')]
    return near_join_gdf_


def check_by_settlement(gdf, settExtent_gdf, type_col, search_distance):
    """
    Check points against settlement extent if points fall on a settlement or not
    based on defined distance
    #==============================#
    :param gdf: a point layer as geopandas dataframe
    :param settExtent_gdf: settlement extent as geopandas dataframe
    :param type_col: settlement type column from settlement extent layer
    :param search_distance: search distance in meter
    :return: a point layer as geopandas dataframe
    """

    # set projection to projected coordinate system
    # ESRI:102023: Africa Equidistant Conic will be used
    gdf.drop(["settlement_type", 'dist_to_settlement_type'], axis=1, inplace=True, errors="ignore")
    gdf_proj = gdf.to_crs("ESRI:102023")
    settExtent_gdf_proj = settExtent_gdf.to_crs("ESRI:102023")

    settExtent_gdf_proj.rename({type_col: "settlement_type"}, axis=1, inplace=True)
    # get nearest feature
    near_join_gdf = geopandas.sjoin_nearest(gdf_proj, settExtent_gdf_proj[["settlement_type", "geometry"]],
                                            max_distance=search_distance, distance_col="dist_to_settlement_type",
                                            how="left")
    near_join_gdf.drop('index_right', axis=1, inplace=True)
    near_join_gdf_ = near_join_gdf.to_crs("EPSG:4326")
    near_join_gdf_["settlement_type"].fillna("Out of a settlement", inplace=True)
    return near_join_gdf_


def check_overlaps(df, POI_name, check_dist_m, long, lat):
    """
    :param df: dataframe
    :param POI_name: name of PoI
    :param check_dist_m: distance for checking overlap
    :param long: long
    :param lat: lat
    """

    spatial_cluster_id_column = 'geo_dbscan_r' + str(check_dist_m) + '_cluster_id'
    # cluster points
    df = create_geo_cluster_column(df, long, lat, check_dist_m, min_samples=2)
    df['is_overlap'] = "NO"
    df_group = df.groupby(spatial_cluster_id_column)
    for index_, group in df_group:
        if group.shape[0] >= 2:
            overlap_name = list(group[POI_name].unique())
            if len(overlap_name) > 1:
                df.loc[df[spatial_cluster_id_column] == index_, 'is_overlap'] = "YES"

    df.drop([spatial_cluster_id_column], axis=1, inplace=True)


def point_pairs_dist_calculation(lon1, lat1, lon2, lat2):
    """
    Calculate distance between two points in km.
    #==============================#
    :param lon1: longitude from point1
    :param lat1:latitude from point1
    :param lon2:longitude from point2
    :param lat2:latitude from point2
    :return: a series of distance in km
    """

    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    newlon = lon2 - lon1
    newlat = lat2 - lat1
    haver_formula = np.sin(newlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(newlon / 2.0) ** 2
    dist = 2 * np.arcsin(np.sqrt(haver_formula))
    km = round(6371 * dist, 2)
    return km


def calculate_dist_point_to_polygon_bdry(gdf_point, gdf_admin_var, gdf_lat_var, gdf_long_var, gdf_polygon,
                                         gdf_polygon_admin_var):
    """
    # Calculate distance (km) from a point to a polygon feature
        # ##===========================================##
        # :param gdf_point: geopandas dataframe
        # :param gdf_admin_var: admin column that indicates a point should be located
        # :param gdf_lat_var: latitude
        # :param gdf_long_var: longitude
        # :param gdf_polygon: geopandas dataframe
        # :param gdf_polygon_admin_var: a column that holds admin names
        # :return: geopandas dataframe
     """

    def closest_point(apoint, points):
        """
        :param apoint: a point
        :param points: set of points
        :return: distance between a points closest point from set of points in km
        """
        closest_index = distance.cdist([apoint], points).argmin()
        return points[closest_index]

    ##==============================================##
    outfield = "dist_to_{}_border_km".format(gdf_polygon_admin_var)
    preclean(gdf_point, gdf_admin_var + "_updated", "temp")
    preclean(gdf_polygon, gdf_polygon_admin_var, "temp")

    for i, row in gdf_point.iterrows():
        if row[gdf_polygon_admin_var + "Match"] == "NO":
            lat, long = gdf_point.loc[i, gdf_lat_var], gdf_point.loc[i, gdf_long_var]

            if lat != 0 and long != 0 and row[gdf_admin_var + "_match_result"] == "YES":
                polygon_name = gdf_point.loc[i, "temp"]

                polygon = gdf_polygon[gdf_polygon["temp"] == polygon_name].reset_index()["geometry"][0]
                if polygon.geom_type == "Polygon":
                    polygon_nodes = list(polygon.exterior.coords)
                    if len(polygon_nodes[0]) >= 3:
                        polygon_nodes = [list(i[:2]) for i in polygon_nodes]

                    long2, lat2 = closest_point((long, lat), polygon_nodes)
                    distance_km = point_pairs_dist_calculation(long, lat, long2, lat2)
                    gdf_point.loc[i, outfield] = distance_km
                elif polygon.geom_type == "MultiPolygon":
                    polygon_nodes = []
                    # [[polygon_nodes.append(i) for i in z.exterior.coords[:2]] for z in list(polygon)]
                    [[polygon_nodes.append(i) for i in z.exterior.coords[:2]] for z in polygon.geoms]
                    if len(polygon_nodes[0]) >= 3:
                        polygon_nodes = [list(i[:2]) for i in polygon_nodes]

                    long2, lat2 = closest_point((long, lat), polygon_nodes)
                    distance_km = point_pairs_dist_calculation(long, lat, long2, lat2)
                    gdf_point.loc[i, outfield] = distance_km

    gdf_point.drop("temp", axis=1, inplace=True, errors="ignore")
    gdf_polygon.drop("temp", axis=1, inplace=True, errors="ignore")


def create_unique_column(df, cols_to_concat=[], new_col_name="unique_name", sep="_"):
    """
    create unique variable to pull match names and match candidates from both table
    :param df: dataframe
    :param cols_to_concat: list of column names to create unique variable
    :param new_col_name: name of the unique variable
    :param sep: unique variable name
    """

    if len(cols_to_concat) >= 1:
        df[new_col_name] = df[cols_to_concat[0]]
        for col in cols_to_concat[1:]:
            df[new_col_name] = df[new_col_name].astype(str) + sep + df[col].astype(str)


def my_random_string(string_length=10):
    """Returns a random string of length string_length."""
    random = str(uuid.uuid4())  # Convert UUID format to a Python string.
    random = random.upper()  # Make all characters uppercase.
    random = random.replace("-", "")  # Remove the UUID '-'.
    return random[0:string_length]  # Return the random string.


def create_uuid_code(df, group_vars, uuid_var_name):
    """
    create uuuid with specified list of variable
    :param df: dataframe
    :param group_vars: list of the variable to consider when create uuid
    :param uuid_var_name: name of uuid field
    """
    
    create_unique_column(df, group_vars, "unique_name_uuid")
    # create uuid
    for name in df["unique_name_uuid"].unique():
        df.loc[df["unique_name_uuid"] == name, uuid_var_name] = my_random_string(string_length=10)
    del df["unique_name_uuid"]


def get_duplicate_count(df, fields_to_check_dup=[], out_field="count"):
    """
    attached number of duplicate points based on specified list of fields
    :param df: dataframe
    :param fields_to_check_dup: list of fields to check duplication
    :param out_field: a field name to hold count
    :return: dataframe
    """

    df.drop([out_field, "unique_name"], axis=1, inplace=True, errors="ignore")
    # create unique column
    create_unique_column(df, fields_to_check_dup, new_col_name="unique_name", sep="_")
    # attached duplicate count
    count_df = df.groupby("unique_name").size().reset_index(name=out_field)
    df = df.merge(count_df, on="unique_name", how="left")
    df.drop(["unique_name"], axis=1, inplace=True, errors="ignore")
    return df


def flag_duplicate_items_in_field(df, field):
    """
    get duplicated items in a field
    :param df: dataframe
    :param field: field name
    :return: list of duplicated items
    """

    dup_item = df[field].tolist()
    duplicate_items = [item for item, count in Counter(dup_item).items() if count > 1]
    df[field + "_isUnique"] = df[field].apply(lambda i: 1 if i in duplicate_items else 0)


def fix_language(df, field_to_clean, language):
    """
    Reformat type of the facilities based on country language
    :param df: dataframe
    :param field_to_clean: field name to reformat
    :param language: French , English or Portuguese

    """

    if language == "French":
        dict_strings = {'De': 'de', 'Sante': 'Santé', 'Hospitalier': 'Hôpitalier',
                        'Hopital': 'Hôpital', 'General': 'Général',
                        'Reference': 'Référence', 'Clinic': 'Clinique', 'Medical': 'Médical',
                        'Maternite': 'Maternité', 'Medico': 'Médico',
                        'Rehabilitation': 'Réhabilitation', 'Prive': 'Privé',
                        'La': 'la', "Privée": "Privé", "Centre Hôpitalier": "Centre Hôpitalier",
                        'Tradi-Praticien': 'Tradipraticien', "Darrondissement": "d'Arrondissement",
                        "Regional": "Régional", "Baptist Hôpital": "Baptist Hospital",
                        "Catholic Hôpital": "Catholic Hospital", "Integre": "Integré", "Pediatrique": "Pédiatrique",
                        "Prière": "Prière", "Medicament": "Médicament"}
    elif language == "Portuguese":
        dict_strings = {'De': 'de', 'Saude': 'Saúde', "Missao": "Missão", "Missionario": "Missionário",
                        "Referencia": "Referência", 'Medico': 'Médico', "Ortopedico": "Ortopédico",
                        "Reabilitacao": "Reabilitação", "Medica": "Médica", "Clinica": "Clínica",
                        "Catolica": "Católica", "Direccao": "Direcção", "Pediatrico": "pediátrico",
                        "General": "Geral", "Darrondissement": "d'Arrondissement"}
    else:
        dict_strings = {}

    # Work with title text
    for key in dict_strings:
        df[field_to_clean].replace(r'\b' + key.title() + r'\b', dict_strings[key], regex=True, inplace=True)


def get_date_as_string():
    today = date.today()
    return today.strftime("%Y%m%d")


def add_g3_required_fields(df, data_source, cntry_iso):
    df['g3_iso'] = cntry_iso
    df['g3_date'] = get_date_as_string()
    df['g3_source'] = data_source
    df['tmp_num'] = df.apply(lambda row: my_random_string(), axis=1)
    create_unique_column(df, cols_to_concat=['g3_source', 'tmp_num'], new_col_name="g3_id", sep="_")
    df.drop(['tmp_num'], inplace=True, axis=1, errors="ignore")
