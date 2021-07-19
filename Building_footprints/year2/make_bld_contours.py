# -*- coding: utf-8 -*-
"""
Spyder Editor

Jolynn Schmidt
jschmidt@ciesin.columbia.edu
"""
import arcpy, os
from arcpy import env
from arcpy.sa import *
import mgrs

from config import Config
cfg = None

env.overwriteOutput = True

# Set coord system to define cell size in meters
env.outputCoordinateSystem = arcpy.SpatialReference(102022)


def check_input_source(sourceFC):
    if not arcpy.Exists(sourceFC):
        print(f'Cannnot find {sourceFC}')
        return False


def update_fields(in_settlements):
    arcpy.AlterField_management(in_settlements, "SUM_bld_area", new_field_alias="sum_bld_area")
    arcpy.AlterField_management(in_settlements, "MIN_bld_area", new_field_alias="min_bld_area")
    arcpy.AlterField_management(in_settlements, "MAX_bld_area", new_field_alias="max_bld_area")


def make_shellup_contours(in_fc, out_fc, base_contour, con_interval):
    """Create shell_up contours"""
    print(f'Making Contours for {in_fc} with a base of {base_contour} and interval of {con_interval}.')
    Contour(in_fc, out_fc, con_interval, base_contour, "", "CONTOUR_SHELL_UP")


def contour_to_singlepart(multipart_contours, out_fc, min_contour):
    """convert a multipart contour to a singlepart contour to create settlement extents"""
    print(f'making selection for a minimum contour of {min_contour} from (multipart_contours).')
    # select the minimum contour
    input_field = "ContourMin"
    input_value = min_contour
    qry = "{}= {}".format(input_field, input_value)
    select_one = arcpy.SelectLayerByAttribute_management(multipart_contours, "NEW_SELECTION", qry)
    # convert selected multipart contour to singlepart
    print('Running multipart to singlepart on the selection.')
    arcpy.MultipartToSinglepart_management(select_one, out_fc)


def join_bld_fp(settlements, out_fc, bld_points):
    """Join building counts to settlement extents"""
    if len(arcpy.ListFields(settlements, "bld_count")) > 0:
        print(f'Building Count field exists')
    else:
        print(f'Adding Building count field')
        arcpy.AddField_management(settlements, field_name="bld_count", field_type="LONG")
    arcpy.SpatialJoin_analysis(settlements, bld_points, out_fc, join_type="KEEP_COMMON")
    arcpy.CalculateField_management(out_fc, "bld_count", '!Join_Count!')


def drop_small_contours(in_contours, max):
    """Drop contours that are less than MAX"""
    # this does not work
    qry = "{} < {}".format("bld_count", max)
    tmp_select = arcpy.SelectLayerByAttribute_management(in_contours, "NEW_SELECTION", qry)
    print(arcpy.GetCount_management(tmp_select))
    arcpy.DeleteFeatures_management(tmp_select)


def make_simple(settlements_in, settlements_out):
    # Eliminate small holes and smooth polygons
    tmp_set = "tmp_m"
    arcpy.management.EliminatePolygonPart(settlements_in, tmp_set, "AREA", 7500, "", "CONTAINED_ONLY")
    # arcpy.env.cartographicPartitions = settlement_parts
    arcpy.cartography.SmoothPolygon(tmp_set, settlements_out, "PAEK", "50")


def make_buffer(in_fc, out_fc, buffer):
    arcpy.Buffer_analysis(in_fc, out_fc, buffer)


def buffer_hamlets(in_settlements, bld_points, out_fc, buffer):
    """Create buffers around settlements that are not within a contour"""
    tmp_select = arcpy.SelectLayerByLocation_management(bld_points, "INTERSECT", in_settlements)
    hamlets = arcpy.SelectLayerByLocation_management(tmp_select, None, None, "", "SWITCH_SELECTION")
    arcpy.Buffer_analysis(hamlets, out_fc, buffer)

def buffer_raster_points(in_settlements, hamlet_buffer, raster_points, out_fc, buffer ):
#    tmp_select = arcpy.SelectLayerByLocation_management(raster_points, "INTERSECT", in_settlements)
#    tmp_select2 = arcpy.SelectLayerByLocation_management(tmp_select, "INTERSECT", hamlet_buffer,"", "ADD_TO_SELECTION")
#    raster_pnts = arcpy.SelectLayerByLocation_management(tmp_select2, None, None, "", "SWITCH_SELECTION")
    arcpy.Buffer_analysis(raster_points, out_fc, buffer)
    arcpy.Append_management(out_fc, hamlet_buffer, "NO_TEST")

def merge_and_dissolve(in_settlements, hamlet_buffers, out_file):
    """merge and dissolve hamlet buffers and settlements"""
    print("Merge starting")
    arcpy.Merge_management([in_settlements, hamlet_buffers], out_file)

#    print(f"Repairing geometry before Dissolve of {out_file}")
#    arcpy.RepairGeometry_management(out_file)

    out_dissolve = out_file + "_dis"
    print("Dissolve starting")
    arcpy.Dissolve_management(out_file, out_dissolve, "", "", "SINGLE_PART")


def add_id_fields(in_settlement):
    arcpy.AddField_management(in_settlement, field_name='x', field_type="DOUBLE")
    arcpy.AddField_management(in_settlement, field_name='y', field_type="DOUBLE")
    arcpy.AddField_management(in_settlement, field_name='mgrs', field_type="TEXT", field_length=50)

    arcpy.CalculateGeometryAttributes_management(in_settlement, [['x', 'INSIDE_X'], ['y', 'INSIDE_Y']],
                                                 coordinate_system="4326")
    m = mgrs.MGRS()
    with arcpy.da.UpdateCursor(in_settlement, ['y', 'x', 'mgrs']) as cursor:
        for row in cursor:
            lat = row[0]
            lon = row[1]
            mgrs_2 = m.toMGRS(lat, lon, MGRSPrecision=2)
            row[2] = mgrs_2
            try:
                cursor.updateRow(row)
            except:
                print(f'Unable to update row')


def increment_duplicates(in_settlement, in_dupes):
    i = 0
    sql = "ORDER BY " + in_dupes + " ASC"
    arcpy.AddField_management(in_settlement, field_name='d_count', field_type="TEXT", field_length=6)
    with arcpy.da.UpdateCursor(in_settlement, [in_dupes, "d_count"], sql_clause=(None, sql)) as cursor:
        for row in cursor:
            if i == 0:  # first time around
                value = row[0]
            if row[0] != value:  # if a new ID
                value = row[0]
                i = 1
            else:  # seen before just add one
                i += 1
            row[1] = i
            cursor.updateRow(row)


def add_mgrs_code(in_settlement):
    arcpy.AddField_management(in_settlement, field_name="mgrs_code", field_type="TEXT", field_length=50)
    arcpy.CalculateField_management(in_settlement, "mgrs_code", '!mgrs! + "_" + !d_count!.zfill(2)')


def find_ssa(in_settlement, min_count):
    """make any builidng over the minimum count an SSA"""
    # make a type filed if we don't have one
    if len(arcpy.ListFields(in_settlement, "type")) > 0:
        print(f'type field exists')
    else:
        print(f'Adding type field')
        arcpy.AddField_management(in_settlement, field_name="type", field_type="TEXT", field_length=16)
    # choose the minimum count that will define an SSA
    input_field = "bld_count"
    input_value = min_count
    qry = "{} >= {}".format(input_field, input_value)
    select_ssa = arcpy.SelectLayerByAttribute_management(in_settlement, "NEW_SELECTION", qry)
    arcpy.CalculateField_management(select_ssa, "type",
                                    "'ssa'",
                                    "PYTHON3")


def find_bua(in_contours, in_settlement, area, min_count):
    """Use a combination of contours and area to find BUA's"""
    # make a type field if we don't have one
    if len(arcpy.ListFields(in_settlement, "type")) > 0:
        print(f'type field exists')
    else:
        print(f'Adding type field')
        arcpy.AddField_management(in_settlement, field_name="type", field_type="TEXT", field_length=16)
    # find conrtours larger than area
    input_field_a = "Shape_Area"
    input_value_a = area
    qry = "{}>= {}".format(input_field_a, input_value_a)
    area_select = arcpy.SelectLayerByAttribute_management(in_contours, "NEW_SELECTION", qry)
    # Use the selected contours to find BUA settlements
    area_loc_select = arcpy.SelectLayerByLocation_management(in_settlement, "INTERSECT", area_select)

    input_field_b = "bld_count"
    input_value_b = min_count
    bld_select = "{} > {}".format(input_field_b, input_value_b)
    bld_count_select = arcpy.SelectLayerByAttribute_management(area_loc_select, "ADD_TO_SELECTION", bld_select)

    arcpy.CalculateField_management(bld_count_select, "type",
                                    "'bua'",
                                    "PYTHON3")


def make_final_layers(in_settlement, settlement_type, out_gdb):
    print(f'making {settlement_type}')
    type_fc = os.path.join(out_gdb, settlement_type)
    input_field = "type"
    type_qry = "{} LIKE '%{}%' And bld_count >= 1".format(input_field, settlement_type)
    type_select = arcpy.SelectLayerByAttribute_management(in_settlement, "NEW_SELECTION", type_qry)
    arcpy.CopyFeatures_management(type_select, type_fc)
    arcpy.AddGlobalIDs_management(type_fc)
    arcpy.Generalize_edit(type_fc, "5 Meters")
    


def main(p_cfg: Config):
    # --------------------------------------------- define variables --------------------------------------------- #
    global cfg
    cfg = p_cfg
    gi = cfg.GDB_INFO
    global in_raster
    in_raster = gi.RASTER_NAME
    global raster_file
    raster_file = os.path.join(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME, gi.RASTER_NAME)

    global working_gdb
    working_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME)
    env.workspace = working_gdb

    global final_gdb
    final_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.OUTPUT_GDB_NAME)

    global building_points
    building_points = gi.BUILDING_POINTS_FEATURE_CLASS
    
    global final_open_gdb
    final_open_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.OPEN_GDB_NAME)
    
    global country_code
    country_code = cfg.COUNTRY_CODE
    
    global raster_name
    raster_name = country_code + "_100_bldCounts"

    # ------------------------------------------------------------------------------------------ #

    if not arcpy.Exists(working_gdb):
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME)
    if not arcpy.Exists(final_gdb):
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.OUTPUT_GDB_NAME)
    if not arcpy.Exists(final_open_gdb):
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.OPEN_GDB_NAME)

    check_input_source(in_raster)

    # Make a set of shell up contours
    contour_base = 1
    contour_interval = 2
    out_contours = in_raster + "_" + str(contour_base) + "_" + str(contour_interval)
    make_shellup_contours(raster_file, out_contours, contour_base, contour_interval)

    # We like the one and up contour so we run with "1"
    min_contour = 1
    sp_contour = cfg.COUNTRY_CODE + "_" + str(min_contour) + "_andUp"
    contour_to_singlepart(out_contours, sp_contour, min_contour)
    # Join building counts to the settlement contours
    contour_count = sp_contour + "_cnt"
    join_bld_fp(sp_contour, contour_count, building_points)

    # We will use buffers for small hamlets so drop contours with 20 or less buildings
    drop_small_contours(contour_count, 20)

    # Create the bufferes around the small hamlets
    buf_hamlets = cfg.COUNTRY_CODE + "_hamlet_buff_65"
    buffer_hamlets(contour_count, building_points, buf_hamlets, "65 Meters")
    
    buf_raster = cfg.COUNTRY_CODE + "_raster_buff_50"
    buffer_raster_points(contour_count, buf_hamlets, gi.RASTER_POINTS_FEATURE_CLASS, buf_raster, "50 Meters" )

    # Merge and disolve small hamlets with the rest of the settlements
    settl = cfg.COUNTRY_CODE + "_settlements_raw"
    settl_dissolve = settl + "_dis"
    merge_and_dissolve(contour_count, buf_hamlets, settl)

#    print(f"Repairing geometry after Dissolve of {settl_dissolve}")
#    arcpy.RepairGeometry_management(settl_dissolve)

    # Add the final building counts
    final_settl = cfg.COUNTRY_CODE + "_settlements"
    arcpy.SummarizeWithin_analysis(settl_dissolve, building_points, final_settl,
                                   'KEEP_ALL', [['bld_area', 'SUM'],
                                                ['bld_area', 'MIN'],
                                                ['bld_area', 'MAX'],
                                                ['tmp_cnt', 'SUM']],
                                   'NO_SHAPE_SUM', '', '', '', '', '')

    if len(arcpy.ListFields(final_settl, "bld_count")) <= 0:
        arcpy.AddField_management(final_settl, "bld_count", "LONG")
    arcpy.CalculateField_management(final_settl, "bld_count", '!SUM_tmp_cnt!')

    # Add global and mgrs codes
    add_id_fields(final_settl)
    increment_duplicates(final_settl, "mgrs")
    add_mgrs_code(final_settl)

    # Find SSA's do this first
    ssa_min_bld_count = 50
    find_ssa(final_settl, ssa_min_bld_count)

    # find BUA after SSA - use a minimum count of 15 with an area of 250,000
    min_contour = 13
    sp_contour_2 = cfg.COUNTRY_CODE + "_" + str(min_contour) + "_andUp"
    contour_to_singlepart(out_contours, sp_contour_2, min_contour)

    contour_area = 400000
    min_bld_count = 3000
    find_bua(sp_contour_2, final_settl, contour_area, min_bld_count)

    # find hamlets
    find_hamlets = arcpy.SelectLayerByAttribute_management(final_settl, "NEW_SELECTION", "type IS NULL")
    arcpy.CalculateField_management(find_hamlets, "type",
                                    "'hamlet'",
                                    "PYTHON3")

    # drop unused fields
    drop_fields = ["PolyDate",
                   "ImgDate",
                   "CAT_ID",
                   "DataSource",
                   "Product",
                   "ORIG_FID",
                   "tmp_cnt",
                   "Shape_Leng",
                   "Join_Count",
                   "TARGET_FID",
                   "SUM_tmp_cnt",
                   "x",
                   "y",
                   "mgrs",
                   "d_count",
                   "OBJECTID_1",
                   "ORIG_FID"]

    # remove small holes and clean fields
    final_settl_simple = final_settl + "_sim"
    arcpy.management.EliminatePolygonPart(final_settl, final_settl_simple, "AREA", 7500, "", "CONTAINED_ONLY")
    arcpy.DeleteField_management(final_settl_simple, drop_fields)
    update_fields(final_settl_simple)

    # make final settlement layers
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
    arcpy.env.preserveGlobalIds = True

    make_final_layers(final_settl_simple, "bua", final_gdb)
    make_final_layers(final_settl_simple, "ssa", final_gdb)
    make_final_layers(final_settl_simple, "hamlet", final_gdb)
    
    new_bua_open = os.path.join(final_open_gdb, "bua_extents")
    new_ssa_open = os.path.join(final_open_gdb, "ssa_extents")
    new_hamlet_open = os.path.join(final_open_gdb, "hamlet_extents")
    
    make_final_layers(final_settl_simple, "bua", final_open_gdb)
    make_final_layers(final_settl_simple, "ssa",  final_open_gdb)
    make_final_layers(final_settl_simple, "hamlet",final_open_gdb)

    bc_raster_in = in_raster + "_bldCounts"
    bc_raster_out = os.path.join(final_gdb, bc_raster_in)
    arcpy.CopyRaster_management(bc_raster_in, bc_raster_out)
    bc_raster_out = os.path.join(final_open_gdb, bc_raster_in)
    arcpy.CopyRaster_management(bc_raster_in, bc_raster_out)


# --------------------------------------------- Initial Processing Begins --------------------------------------------- #
if __name__ == '__main__':
    cfg = Config()
    main(cfg)
