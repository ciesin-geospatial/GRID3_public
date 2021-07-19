# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 10:49:05 2019

@author: jschmidt

This script creates two rasters.
1. car_100 used for creating contours
2. car_100_bldCount as a final product for distribution
"""
import arcpy, os
from arcpy import env
from arcpy.sa import *

from config import Config
cfg = None
env.overwriteOutput = True

def check_input_source(sourceFC):
    if not arcpy.Exists(sourceFC):
        print(f'Cannnot find {sourceFC}')
        return False
  
def poly_to_point(sourceFC, processedFC):
    """convert building footprints to points for ease of processing"""
    print(f'Processing {sourceFC}...')
    arcpy.FeatureToPoint_management(sourceFC, processedFC, "INSIDE")
    

def point_to_raster(in_points, out_raster, snap_raster):
    """create a raster that can be used to make contours and a second of building counts"""
    print(f'Converting {in_points} to a raster')
    gi = cfg.GDB_INFO
# add field for default values 
    if len(arcpy.ListFields(in_points,"tmp_cnt"))<1:
         print(f'Adding tmp field')  
         arcpy.AddField_management(in_points, field_name="tmp_cnt", field_type="SHORT")
         arcpy.CalculateField_management(in_points, "tmp_cnt", "1")
    else:
        print(f'Tmp count field exists')  
# convert points to raster
    print('Creating raster')
    tmp_raster = out_raster + "_bldCounts"
    tmp_raster_points = gi.RASTER_POINTS_FEATURE_CLASS
    arcpy.env.extent = snap_raster
    arcpy.env.snapRaster = snap_raster
    arcpy.PointToRaster_conversion(in_points, "tmp_cnt", tmp_raster, "SUM", "")
    arcpy.RasterToPoint_conversion(tmp_raster,tmp_raster_points,"VALUE")
# reclassify nodata to zero
    print('Reclassify NoData to zero')
    max_cnt_out = arcpy.GetRasterProperties_management(tmp_raster, "MAXIMUM")
    max_cnt = int(max_cnt_out.getOutput(0))
    remap = RemapValue([["NODATA", 0]])
    outReclassify = Reclassify(tmp_raster, "value", remap, "DATA")
# save a copy for building counts
    
    outReclassify.save(tmp_raster)    
# max out the count at 150 - this makes better countours 
    if max_cnt > 150:
        remap2 = RemapRange([[151, max_cnt, 150]])
        outReclassify = Reclassify(outReclassify, "value", remap2, "DATA")
        
    tmp_raster_150 = out_raster + "_bldCounts_max150"
    outReclassify.save(tmp_raster_150)



    # the reprojection fails, so we convert to tif, maybe because attribute tables are not included, not sure 
    arcpy.RasterToOtherFormat_conversion( Input_Rasters= os.path.join(
        gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME, gi.RASTER_NAME + "_bldCounts_max150"), 
        Output_Workspace=gi.GDB_PARENT_DIR, Raster_Format="TIFF")

# Save the contour raster with an equal area projection
    
    arcpy.env.extent = None
    arcpy.env.snapRaster = None 
    
    arcpy.ProjectRaster_management(os.path.join(gi.GDB_PARENT_DIR, gi.RASTER_NAME + "_bldCounts_max150.tif"), 
        os.path.join(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME, out_raster), 102022)

def raster_to_point(in_raster, out_points):
    arcpy.RasterToPoint_conversion(in_raster, out_points, "VALUE")
                

def main(p_cfg: Config):
    # --------------------------------------------- Define Variables --------------------------------------------- #
    # Input data sources
    global cfg
    cfg = p_cfg
    gi = cfg.GDB_INFO

    pbf = cfg.PROCESSED_BUILDING_FOOTPRINTS
    raw_file = os.path.join(pbf.GDB_PARENT_DIR, pbf.GDB_NAME, pbf.FEATURE_CLASS)
    # Output data sources

    working_gdb = os.path.join(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME)
    env.workspace = working_gdb

    # ------------------------------------------------------------------------------------------ #
    # create output GDB if needed
    if not arcpy.Exists(working_gdb):
        os.makedirs(gi.GDB_PARENT_DIR, exist_ok=True)
        arcpy.CreateFileGDB_management(gi.GDB_PARENT_DIR, gi.WORK_GDB_NAME)

    # Convert polygons to points
    print("Converting polygons to points")
    bld_pnts = gi.BUILDING_POINTS_FEATURE_CLASS
    poly_to_point(raw_file, bld_pnts)
    # Points to rasters
    print("Convering points to rasters")

    point_to_raster(bld_pnts, gi.RASTER_NAME, cfg.RASTER_GRID_PATH)



# --------------------------------------------- Initial Processing Begins --------------------------------------------- #
if __name__ == '__main__':
    cfg = Config()
    main(cfg)
