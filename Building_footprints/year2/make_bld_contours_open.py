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

from make_bld_contours import *
from config import Config
cfg = None

env.overwriteOutput = True

# Set coord system to define cell size in meters
env.outputCoordinateSystem = arcpy.SpatialReference(102022)



def make_final_layers(in_settlement, settlement_type, out_fc, out_gdb):
    print(f'making {settlement_type}')
    type_fc = os.path.join(out_gdb, out_fc)
    input_field = "type"
    type_qry = "{} LIKE '%{}%' And bld_count >= 1".format(input_field, settlement_type)
    type_select = arcpy.SelectLayerByAttribute_management(in_settlement, "NEW_SELECTION", type_qry)
    arcpy.CopyFeatures_management(type_select, type_fc)
    arcpy.AddGlobalIDs_management(type_fc)
#

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

    # ------------------------------------------------------------------------------------------ #

    if not arcpy.Exists(working_gdb):
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME)
    if not arcpy.Exists(final_gdb):
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.OUTPUT_GDB_NAME)

    check_input_source(in_raster)

    # Make a set of shell up contours
    contour_base = 1
    contour_interval = 2
    out_contours = in_raster + "_" + str(contour_base) + "_" + str(contour_interval)
#    make_shellup_contours(raster_file, out_contours, contour_base, contour_interval)

    # We like the one and up contour so we run with "1"
    min_contour = 1
    sp_contour = cfg.COUNTRY_CODE + "_" + str(min_contour) + "_andUp"
#    contour_to_singlepart(out_contours, sp_contour, min_contour)
    # Join building counts to the settlement contours
    contour_count = sp_contour + "_cnt"
#    join_bld_fp(sp_contour, contour_count, building_points)

    # We will use buffers for small hamlets so drop contours with 20 or less buildings
#    drop_small_contours(contour_count, 20)

    # Create the bufferes around the small hamlets
    buf_hamlets = cfg.COUNTRY_CODE + "_hamlet_buff_65"
    buffer_hamlets(contour_count, building_points, buf_hamlets, "65 Meters")

    # Merge and disolve small hamlets with the rest of the settlements
    settl = cfg.COUNTRY_CODE + "_settlements_raw_o"
    settl_dissolve = settl + "_dis"
    merge_and_dissolve(contour_count, buf_hamlets, settl)

    # Add the final building counts
    final_settl = cfg.COUNTRY_CODE + "_settlements_o"
    arcpy.SummarizeWithin_analysis(settl_dissolve, building_points, final_settl,
                                   'KEEP_ALL', [['tmp_cnt', 'SUM']],
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
#    update_fields(final_settl_simple)

    # make final settlement layers
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
    arcpy.env.preserveGlobalIds = True

    make_final_layers(final_settl_simple, "bua", "bua_o", final_gdb)
    make_final_layers(final_settl_simple, "ssa",  "ssa_o", final_gdb)
    make_final_layers(final_settl_simple, "hamlet", "hamlet_o", final_gdb)

#    bc_raster_in = in_raster + "_bldCounts"
#    bc_raster_out = os.path.join(final_gdb, bc_raster_in)
#    arcpy.CopyRaster_management(bc_raster_in, bc_raster_out)


# --------------------------------------------- Initial Processing Begins --------------------------------------------- #
if __name__ == '__main__':
    cfg = Config()
    main(cfg)
