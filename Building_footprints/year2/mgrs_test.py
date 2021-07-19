# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 08:54:34 2020

@author: jschmidt
"""

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
            mgrs_2 = m.toMGRS(lat, lon, MGRSPrecision=2).decode('utf-8')
            row[2] = mgrs_2
            try:
                cursor.updateRow(row)
            except:
                print(f'Unable to update row')