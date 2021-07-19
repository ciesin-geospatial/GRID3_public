#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      jolynn
#
# Created:     26/05/2016
# Copyright:   (c) jolynn 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import arcpy, os
def main():
    Workspace = r"D:\GRID3\provinces\Lomami"
    arcpy.env.workspace = Workspace
# list map docs
    mxdList = arcpy.ListFiles("*.mxd")
    #mxdList = ["CWA_Permit.mxd"]
    for file in mxdList:
        filePath = "D:\GRID3\provinces\Lomami\%s" % file
        print filePath
        mxd = arcpy.mapping.MapDocument(filePath)
        mxd.findAndReplaceWorkspacePaths(r"D:\GRID3\provinces\Lomami\maxar_backup", r"D:\GRID3\provinces\shapes")
        mxd.relativePaths = True
        try:
            mxd.save()
        except:
            pass




if __name__ == '__main__':
    main()
