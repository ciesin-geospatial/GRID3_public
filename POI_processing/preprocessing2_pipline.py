"""
this script does exploratory data analyses on a PoI table
these columns will be added output table
>> poi_code:unique id for each entity based on poi_name_var and admin names
>> poi_code_isUnique:indicates if a entity duplicated: 1=duplicate, 0=unique
>> settlement_type:settlement extent type that points are located.
    categories: bua, ssa, hamlets and out of a settlement (more than 250m to a settlement extent)
>> dist_to_settlement_type:Distance between point and a settlement extent
>> is_overlap:indicates if more than two points have the same lat/long
>> *_bryMatch: indicates if a point fall into respective admin boundary
>> *_clean_match_name:indicates the admin name from admin boundary that match to the  admin name from PoI table
>> *_clean_match_result:indicates  if the admin name from admin boundary that match to the  admin name from PoI table
>> *_clean_match_score:indicates  % match between the admin name from admin boundary and  the admin name from PoI table
    Over 80% accepted as good match
>> *_clean_match_type:fuzzy match method
>> dist_to_*_bry_border_km:distance from a point to a admin boundary if the point falls out if the respective the admin boundary
>> geo_dbscan_r25_cluster_id:points that are 25m distance to each other have the same id number
>> geo_dbscan_r50_cluster_id:points that are 50m distance to each other have the same id number
"""

from matching.matching_utilities import fuzzy_match
import configparser
from dictionaries.dictionary_utilities import *


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
        poi_input_dir = config_general['poi_input_dir']
        poi_input_filename = config_general['poi_input_filename']
        poi_output_dir = config_general['poi_output_dir']
        poi_data_type = config_general['poi_data_type']

        poi_lat_var = config_general['poi_lat_field']
        poi_long_var = config_general['poi_long_field']
        language = config_general['language']
        country_ISO = config_general['country_ISO']

        preprocessing1_config = config['preprocessing1']
        poi_input_extension_type = preprocessing1_config['poi_output_extension_type']
        poi_output_extension_type = preprocessing1_config['poi_output_extension_type']

        preprocessing2_config = config['preprocessing2']
        poi_name_var = preprocessing2_config['poi_field']
        poi_admin1 = preprocessing2_config['poi_admin1']
        poi_admin2 = preprocessing2_config['poi_admin2']

        admin_bdry_file = preprocessing2_config["admin_bdry_file"]
        admin1_bdry_var = preprocessing2_config["admin1_bdry_var"]
        admin2_bdry_var = preprocessing2_config["admin2_bdry_var"]
        path_sett_extent = preprocessing2_config["path_sett_extent"]
    except KeyError as ke:
        print("Can't find section or key '" + ke.args[0] + "' in config file '" + config_file + "'")
        return()

    if poi_admin1 == "" and poi_admin2 == "":
        abort("either poi_admin1 and/or poi_admin2 required to be specified")

    # poi_type_var = "sub_type"
    pot_output_name_field, poi_output_type_field = get_poi_labels(poi_data_type)

    # get our input and output full paths
    poi_input_table_basename = poi_input_filename.split(".")[0]
    poi_input_full_filename = os.path.join(poi_output_dir, poi_input_table_basename + "_preprocessing1" + poi_output_extension_type)

    poi_output_table_name = poi_input_table_basename + "_preprocessing2.gpkg"
    poi_output_full_filename = os.path.join(poi_output_dir, poi_output_table_name)

    # make sure everything exists
    if not os.path.exists(poi_output_dir):
        abort("can't save output - output directory doesn't exists: " + str(poi_output_dir))
    sanity_check_file(poi_input_full_filename)
    sanity_check_file(admin_bdry_file)
    sanity_check_file(path_sett_extent)

    # read poi_input_filename
    print("Loading poi file " + poi_input_full_filename + " ...")
    point_gdf = read_data(poi_input_full_filename, poi_lat_var, poi_long_var)
    sanity_check_df(point_gdf, poi_input_filename, [poi_name_var, poi_lat_var, poi_long_var, poi_admin1, poi_admin2])

    # read boundary file
    print("Loading boundary file " + admin_bdry_file)
    admin_bdry_gdf = read_data(admin_bdry_file)
    check_fields = [admin1_bdry_var]
    if admin2_bdry_var != "":
        check_fields.append(admin2_bdry_var)
    sanity_check_df(admin_bdry_gdf, admin_bdry_file, check_fields)

    # read settlement extent
    print("Loading settlement file " + path_sett_extent + " ...")
    sett_extent = read_data(path_sett_extent)

    # Clean facility name, admin1 and admin2
    print("Cleaning input variables...")
    point_gdf[poi_lat_var].fillna(0, inplace=True)
    point_gdf[poi_long_var].fillna(0, inplace=True)

    if poi_admin1 != "":
        preclean(admin_bdry_gdf, admin1_bdry_var, "admin1_bry", remove_accent=True)

    if poi_admin2 != "":
        preclean(admin_bdry_gdf, admin2_bdry_var, "admin2_bry", remove_accent=True)

    # fill type by  with generic type of type is missing
    print("Filling missing types...")
    if poi_output_type_field is not None:
        point_gdf[poi_output_type_field].fillna(value=poi_data_type, inplace=True)

    # fill facility name with type if facility name do not have name info
    print("Filling no names with types...")
    point_gdf[poi_name_var].fillna(point_gdf[poi_output_type_field], inplace=True)

    # create facility unique id with combination of poi_admin1, poi_admin2,and poi_name_var
    print("Creating uuid...")
    uuid_var_list = [poi_name_var]
    if poi_admin1 != "":
        uuid_var_list.append(poi_admin1)
    if poi_admin2 != "":
        uuid_var_list.append(poi_admin2)
    create_uuid_code(point_gdf, uuid_var_list, "poi_code")

    # flag if any facility is duplicated based on mfl_uuid
    print("Flagging duplicate entities...")
    flag_duplicate_items_in_field(point_gdf, "poi_code")

    # reformat facility types
    print("Reformatting types based on language...")
    if language != "English":
        fix_language(point_gdf, poi_output_type_field, language)

    # check by settlement extent
    print("Check PoI with settlement extent...")
    point_gdf = check_by_settlement(point_gdf, sett_extent, "type", 100000)
    point_gdf.loc[point_gdf["dist_to_settlement_type"] >= 250, "settlement_type"] = "Out of a settlement"

    # flag overlapped points
    print("Check records identical lat/long...")
    check_overlaps(point_gdf, poi_output_type_field, 1, poi_long_var, poi_lat_var)

    # Check if points fall into right admin1 boundary
    print("Check if points fall in to right admin units...")
    if poi_admin1 != "":
        # Check if points fall into right admin1 boundary
        point_gdf = check_by_admin(point_gdf, poi_admin1, admin_bdry_gdf, "admin1_bry")
        point_gdf = point_gdf[~point_gdf.index.duplicated(keep='first')]

    # Check if points fall into right admin2 boundary
    if poi_admin2 != "":
        point_gdf = check_by_admin(point_gdf, poi_admin2, admin_bdry_gdf, "admin2_bry")
        point_gdf = point_gdf[~point_gdf.index.duplicated(keep='first')]

    # match admin1 names
    print("Matching admin names...")

    if poi_admin1 != "":
        point_gdf[poi_admin1].fillna("Missing", inplace=True)
        fuzzy_match(point_gdf, poi_admin1, admin_bdry_gdf, "admin1_bry", None,
                    match_level="", input_table_level_vars=[],
                    match_table_level_vars=[])
        point_gdf[poi_admin1].replace("Missing", np.nan, inplace=True)

    # match admin2 names
    if poi_admin2 != "":
        point_gdf[poi_admin2].fillna("Missing", inplace=True)
        input_table_level_vars = []
        match_table_level_vars = []
        if poi_admin1 != "":
            input_table_level_vars = [poi_admin1 + "_updated"]
            match_table_level_vars = ["admin1_bry" + "_cleaned"]
        fuzzy_match(point_gdf, poi_admin2, admin_bdry_gdf, "admin2_bry", None,
                    match_level="with level", input_table_level_vars=input_table_level_vars,
                    match_table_level_vars=match_table_level_vars)
        point_gdf[poi_admin2].replace("Missing", np.nan, inplace=True)

    # check distance between points and admin boundary if point is outside the respective admin boundary
    print("Calculating distance to admin boundaries for points that fall outside of right  admin units...")
    if poi_admin1 != "":
        calculate_dist_point_to_polygon_bdry(point_gdf, poi_admin1, poi_lat_var, poi_long_var,
                                             admin_bdry_gdf, "admin1_bry")

    # check distance between points and admin boundary if point is outside respective admin boundary
    if poi_admin2 != "":
        calculate_dist_point_to_polygon_bdry(point_gdf, poi_admin2, poi_lat_var, poi_long_var,
                                             admin_bdry_gdf, "admin2_bry")

    # check if points are clusters in 25 and 50 meters
    print("Flags clustered points...")
    create_geo_cluster_column(point_gdf, poi_long_var, poi_lat_var, 25, min_samples=2)
    point_gdf.loc[point_gdf[poi_lat_var] == 0, "geo_dbscan_r25_cluster_id"] = np.nan
    create_geo_cluster_column(point_gdf, poi_long_var, poi_lat_var, 50, min_samples=2)
    point_gdf.loc[point_gdf[poi_lat_var] == 0, "geo_dbscan_r50_cluster_id"] = np.nan

    # make lat long == 0 to no data
    point_gdf.loc[point_gdf[poi_lat_var] == 0, poi_lat_var] = np.nan
    point_gdf.loc[point_gdf[poi_long_var] == 0, poi_long_var] = np.nan
    point_gdf.loc[point_gdf[poi_lat_var].isnull(), "settlement_type"] = "NA"
    point_gdf.loc[point_gdf[poi_lat_var].isnull(), "dist_to_settlement_type"] = -1
    point_gdf.loc[point_gdf[poi_lat_var].isnull(), "is_overlap"] = "NA"
    point_gdf.loc[point_gdf[poi_lat_var].isnull(), "dist_to_settlement_type"] = -1

    if poi_admin1 != "":
        point_gdf.loc[point_gdf[poi_lat_var].isnull(), "dist_to_admin1_bry_border_km"] = -1
        point_gdf.loc[point_gdf[poi_lat_var].isnull(), "admin1_bryMatch"] = "NA"
    if poi_admin2 != "":
        point_gdf.loc[point_gdf[poi_lat_var].isnull(), "dist_to_admin2_bry_border_km"] = -1
        point_gdf.loc[point_gdf[poi_lat_var].isnull(), "admin2_bryMatch"] = "NA"

    # if poi_lat_var != "":
    #     get_min_resolution(point_gdf, poi_lat_var, poi_long_var)

    print("Starting Export ...", end="")
    point_gdf.drop(['Unnamed: 0', 'dist_to_admin1_bry', 'dist_to_admin2_bry',
                    'admin1_clean_match_uuid', 'admin2_clean_match_uuid', 'admin1_bry_clean', 'admin2_bry_clean'],
                   axis=1, inplace=True, errors="ignore")
    poi_output_full_filename = write_data(point_gdf, poi_output_full_filename)
    print(f"output table saved to: {poi_output_full_filename}")

    # We don't usually want to export our boundaries -
    # especially since shape files inexplicably change columns to lowercase
    # print("Exporting boundaries ...", end="")
    # if poi_admin1 is not None:
    #     bndry_output = write_data(admin_bdry_gdf, admin_bdry_file + "_tmp")
    # print(f"boundaries saved to: {bndry_output}")


if __name__ == '__main__':
    main()
