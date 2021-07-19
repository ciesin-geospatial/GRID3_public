import os
import arcpy

in_countries = [
"ETH",
"GMB",
"KEN",
"LBR",
# "MLI",
"NER",
"NGA",
"SDN",
"SLE",
"SSD",
"ZMB",
]


base_dir = "D:\GRID"
processed_dir = "Processed"
out_dir = "DIGITAL_GLOBE"

for c in in_countries:
    cur_gdb = os.path.join(base_dir, c,  processed_dir, c + "_Processing.gdb")
    out_gdb = os.path.join(base_dir, c, "DIGITAL_GLOBE", c + ".gdb")
    print(cur_gdb)
    print(out_gdb)
    points = c + "_blding_pnts"
    settl = c +"_settlements_o"
    cur_pnts = os.path.join(cur_gdb, points)
    out_pnts = os.path.join(out_gdb, points)
    cur_settl = os.path.join(cur_gdb, settl)
    out_settl = os.path.join(out_gdb, settl)

    try:
        arcpy.CopyFeatures_management(cur_pnts, out_pnts)
        arcpy.CopyFeatures_management(cur_settl, out_settl)
    except:
        print("Unable to copy features")



