"""
This script runs through some loading and saving permutations to confirm our methods all work
"""

from utilities import read_data, write_data
from arcgis_utilities import create_workspace
import os

# supported_file_types = ["csv", "excel", "shape", "gpkg", "feature"]
extensions = [".csv", ".xlsx", ".shp", ".gpkg", ".gdb"]

# file types, want to test csv/excel with and without geometry
# need these pieces separate for ease of processing
base_dir = "test_data"
feature_name = "/test_feature"
input_files = [
    "csvtest.csv",
    "csvtest_latlong.csv",
    "xlstest.xlsx",
    "xlstest_latlong.xlsx",
    "shptest.shp",
    "gtest.gpkg",
    "gdbtest.gdb"
]

for in_file in input_files:

    load_file = os.path.join(base_dir, in_file)

    if ".gdb" in in_file:
        load_file = load_file + feature_name  # add our feature name if it's a gdb

    print("Reading " + load_file)
    df = read_data(load_file)
    base_filename = os.path.splitext(in_file)[0]  # strip the extension for creating output files

    for extension in extensions:
        out_file = base_filename + "_out" + extension

        if ".gdb" in extension:
            print("creating workspace:" + os.path.join(base_dir, "output") + "/" + out_file)
            create_workspace(os.path.join(base_dir, "output"), out_file, use_existing_gdb=False)
            out_file = out_file + feature_name  # add our feature to our gdb

        out_full_file = os.path.join(base_dir, "output", out_file)

        print("Writing " + out_full_file + " ... ", end="")
        res = write_data(df, out_full_file)
        print(res)

