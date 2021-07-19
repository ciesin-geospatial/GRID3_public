# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import arcpy, os
from arcpy import env
# from arcpy import metadata as md
from arcpy.sa import *
import mgrs

from config import Config
cfg = None

env.overwriteOutput = True

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
    # arcpy.AddField_management(in_settlement, field_name="mgrs_code", field_type="TEXT", field_length=50)
    arcpy.CalculateField_management(in_settlement, "mgrs_code", '!mgrs! + "_a" + !d_count!.zfill(2)')


def main(p_cfg: Config):
    # --------------------------------------------- define variables --------------------------------------------- #
    global cfg
    cfg = p_cfg
    gi = cfg.GDB_INFO

    global final_gdb
    final_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.OUTPUT_GDB_NAME)
    
    global final_agg_gdb
    final_agg_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.AGG_GDB_NAME)

    global final_ext_gdb
    final_ext_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.EXT_GDB_NAME)
    
    global final_open_gdb
    final_open_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.OPEN_GDB_NAME)
    
    global country_code
    country_code = cfg.COUNTRY_CODE
    
    global raster_name
    raster_name = country_code + "_100_bldCounts"
    
    global in_raster
    in_raster = os.path.join(gi.GDB_PARENT_DIR, gi.OUTPUT_GDB_NAME, raster_name)

    global out_raster
    out_raster = os.path.join(gi.GDB_PARENT_DIR, gi.AGG_GDB_NAME, raster_name)
    
#    global metadata_dir
#    metadata_dir = cfg.METADATA_DIR
    
    # Phase I output 
    bua_ext = os.path.join(final_gdb, "bua_non_extended")
    ssa_ext = os.path.join(final_gdb, "ssa_non_extended")
    hamlet_ext = os.path.join(final_gdb, "hamlet")
    
    new_bua_ext = os.path.join(final_agg_gdb, "bua")
    new_ssa_ext = os.path.join(final_agg_gdb, "ssa")
    new_hamlet_ext = os.path.join(final_agg_gdb, "hamlet")

    # Phase II output 
    bua_agg = os.path.join(final_gdb, "bua")
    ssa_agg = os.path.join(final_gdb, "ssa")
    ha_agg = os.path.join(final_gdb, "ha")
    
    new_bua_agg = os.path.join(final_agg_gdb, "bua_agg")
    new_ssa_agg = os.path.join(final_agg_gdb, "ssa_agg")
    new_ha_agg = os.path.join(final_agg_gdb, "ha")
    
#    bua_agg_metadata = os.path.join(final_agg_gdb, country_code + "_bua_restricted.xml")

    # Open data output
    
#    bua_open = os.path.join(final_gdb, "bua_o")
#    ssa_open = os.path.join(final_gdb, "ssa_o")
#    hamlet_open = os.path.join(final_gdb, "hamlet_o")
#    
#    new_bua_open = os.path.join(final_open_gdb, "bua_extents")
#    new_ssa_open = os.path.join(final_open_gdb, "ssa_extents")
#    new_hamlet_open = os.path.join(final_open_gdb, "hamlet_extents")

    # ------------------------------------------------------------------------------------------ #
    # make final settlement layers
    if not arcpy.Exists(final_agg_gdb):
        print(f"Creating {final_agg_gdb}")
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.AGG_GDB_NAME)      
        
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
    arcpy.env.preserveGlobalIds = True

    # Add global and mgrs codes
    # drop unused fields
    drop_fields = ["x",
                   "y",
                   "mgrs",
                   "d_count"]
    
    if arcpy.Exists(bua_agg):
        add_id_fields(bua_agg)
        increment_duplicates(bua_agg, "mgrs")
        add_mgrs_code(bua_agg)
        arcpy.DeleteField_management(bua_agg, drop_fields)
        arcpy.CalculateField_management(bua_agg, "type", "'bua'", "PYTHON3")
        
        add_id_fields(ssa_agg)
        increment_duplicates(ssa_agg, "mgrs")
        add_mgrs_code(ssa_agg)
        arcpy.DeleteField_management(ssa_agg, drop_fields)
        arcpy.CalculateField_management(ssa_agg, "type", "'ssa'", "PYTHON3")
        
        add_id_fields(ha_agg)
        increment_duplicates(ha_agg, "mgrs")
        add_mgrs_code(ha_agg)
        arcpy.DeleteField_management(ha_agg, drop_fields)
        arcpy.CalculateField_management(ha_agg, "type", "'ha'", "PYTHON3")
        

        
        # copy over aggrigated features
        print(f"Copy over aggrigated features...")    
        arcpy.CopyFeatures_management(bua_agg, new_bua_agg)
        arcpy.CopyFeatures_management(ssa_agg, new_ssa_agg)
        arcpy.CopyFeatures_management(ha_agg, new_ha_agg)
        arcpy.CopyRaster_management(in_raster, out_raster)
        
        # copy over extent features 
        print(f"Copy over extents features...")
        arcpy.CopyFeatures_management(bua_ext, new_bua_ext)
        arcpy.CopyFeatures_management(ssa_ext, new_ssa_ext)
        arcpy.CopyFeatures_management(hamlet_ext, new_hamlet_ext)
    
#    if arcpy.Exists(bua_open):
#        if not arcpy.Exists(final_open_gdb):
#            print(f"Creating {final_open_gdb}")
#            arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.OPEN_GDB_NAME)
#        # copy over extent features 
#        print(f"Copy over open features...")
#        arcpy.CopyFeatures_management(bua_open, new_bua_open)
#        arcpy.RepairGeometry_management(new_bua_open)
#        arcpy.CopyFeatures_management(ssa_open, new_ssa_open)
#        arcpy.RepairGeometry_management(new_ssa_open)
#        arcpy.CopyFeatures_management(hamlet_open, new_hamlet_open)
#        arcpy.RepairGeometry_management(new_hamlet_open)
    
#    # copy xml
#    print(f"Adding Metadata...")
#    # Get the standard-format metadata XML file's object
#    src_csdgm_path = bua_agg_metadata
## Get the target item's Metadata object
#    tgt_item_md = md.Metadata(new_bua_agg)
## Import the standard-format metadata content to the target item
#    if not tgt_item_md.isReadOnly:
#        print('adding metadata')
#        tgt_item_md.importMetadata(src_csdgm_path, 'ISO19139_UNKNOWN')
#        tgt_item_md.save()

    

# --------------------------------------------- Initial Processing Begins --------------------------------------------- #
if __name__ == '__main__':
#    class Messenger(object):
#        def addMessage(self, message):
#            print(message)
    cfg = Config()
    main(cfg)
