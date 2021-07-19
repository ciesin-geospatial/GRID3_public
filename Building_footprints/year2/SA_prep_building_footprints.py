# -*- coding: utf-8 -*-
"""
Created on Tue Dec 10 10:49:05 2019

@author: jschmidt

This script is used to create a geodatabase that contains a single buildings
file that will be used for processing. 
"""
import arcpy, os
from arcpy import env
from config import Config
env.overwriteOutput = True


def main(cfg):
    def add_area(sourceFC):
        """ Create a field and populate it with the area in meters"""
        if len(arcpy.ListFields(sourceFC,"bld_area"))<1:
          print(f'Adding building area field to {sourceFC}')
          arcpy.AddField_management(sourceFC, field_name="bld_area", field_type="double")
          arcpy.CalculateField_management(sourceFC, "bld_area", "!shape.area!", "PYTHON3")
        else:
          print(f'building area field exists in {sourceFC}')

    def merge_and_project(FC_list, out_FC):
        """Merge BFP into a single file with wgs84"""
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
        arcpy.Merge_management(FC_list, out_FC)



# --------------------------------------------- define variables --------------------------------------------- # 

    working_gdb = os.path.join(cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_PARENT_DIR,
                               cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_NAME)

    raw_file = os.path.join(working_gdb, cfg.PROCESSED_BUILDING_FOOTPRINTS.FEATURE_CLASS)
    
# when using a gdb
    #utm_shapes = arcpy.ListFeatureClasses()
      
# when using a shape file  

    arcpy.env.workspace = working_gdb
# ------------------------------------------------------------------------------------------ #    
    for shape in cfg.BUILDING_FOOTPRINT_SHAPEFILE_PATHS:
        add_area(shape)
      
#create output GDB if needed    
    if not arcpy.Exists(working_gdb):
        os.makedirs(cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_PARENT_DIR, exist_ok=True)
        
        arcpy.CreateFileGDB_management(
            cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_PARENT_DIR,
            cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_NAME)
    
    merge_and_project(cfg.BUILDING_FOOTPRINT_SHAPEFILE_PATHS, raw_file)
    
# fix geometry from merge
    arcpy.RepairGeometry_management(raw_file)

if __name__ == '__main__':
    main(Config())
