import glob
import shutil
from pathlib import Path
from typing import Dict, Union, Tuple
from config import Config
import os
import logging
import make_bld_raster
import make_bld_contours
import make_hamlet_areas_and_extend_buas

log = logging.getLogger(__name__)


def init_logging(is_verbose: bool):
    """
    Initializes logger.

    Disables non grid3 related logs

    :param is_verbose: False will disable all loggers beloging to trace
    """
    log_level = logging.DEBUG
    log_format = "  %(asctime)-15s %(levelname)-8s %(name)-25s %(lineno)-5d | %(message)s"

    logging.root.setLevel(log_level)

    stream = logging.StreamHandler()
    stream.setLevel(log_level)

    formatter = logging.Formatter(log_format)
    stream.setFormatter(formatter)

    logging.root.addHandler(stream)

    logging.getLogger("fiona").setLevel(logging.CRITICAL)
    logging.getLogger("matplotlib").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    if not is_verbose:
        logging.getLogger("trace").setLevel(logging.CRITICAL)

def test1():
    bldg_path = Path(__file__).parent / "test_input" / "ner_bua" / "NerTestBUA.gdb"

    env_vars = {"COUNTRY_CODE": "TEST1",
                "RASTER_GRID_PATH": r"D:\GRID\ReferenceRasters\ner_px_area_100m.tif",
                "BUILDING_FOOTPRINT_SHAPEFILE_PATHS": ""
                }

    os.environ.update(env_vars)

    return bldg_path

def test2():
    bldg_path = Path(__file__).parent / "test_input" / "test2" / "test2.gdb"

    env_vars = {"COUNTRY_CODE": "TEST2",
                "RASTER_GRID_PATH": r"D:\GRID\ReferenceRasters\ner_px_area_100m.tif",
                "BUILDING_FOOTPRINT_SHAPEFILE_PATHS": ""
                }

    os.environ.update(env_vars)

    return bldg_path


def test3():
    bldg_path = Path(__file__).parent / "test_input" / "test3" / "test3.gdb"

    env_vars = {"COUNTRY_CODE": "TEST3",
                "RASTER_GRID_PATH": r"D:\GRID\ReferenceRasters\ner_px_area_100m.tif",
                "BUILDING_FOOTPRINT_SHAPEFILE_PATHS": ""
                }

    os.environ.update(env_vars)

    return bldg_path


def run_test(bldg_path):


    cfg = Config()
    gdb_path = Path(cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_PARENT_DIR) / cfg.PROCESSED_BUILDING_FOOTPRINTS.GDB_NAME

    log.info(f"Making sure {gdb_path} exists")

    if not gdb_path.exists():
        shutil.copytree(bldg_path, gdb_path)
    else:
        log.info(f"{gdb_path} exists")

    gi = cfg.GDB_INFO
    expected_raster_path = Path(gi.GDB_PARENT_DIR) / ( gi.RASTER_NAME + "_bldCounts_max150.tif")

    if not expected_raster_path.exists():
        log.info(f"Making the raster -- {expected_raster_path}")
        make_bld_raster.main(cfg)
    else:
        log.info(f"Raster already exists -- {expected_raster_path}")


    processing_gdb = Path(gi.GDB_PARENT_DIR) / gi.WORK_GDB_NAME
    backup_processing_gdb = Path(gi.GDB_PARENT_DIR) / ("backup_" + gi.WORK_GDB_NAME)

    settlements_gdb = Path(gi.GDB_PARENT_DIR) / gi.OUTPUT_GDB_NAME
    backup_settlements_gdb = settlements_gdb.parent / ("backup_" + gi.OUTPUT_GDB_NAME)

    if not settlements_gdb.exists():
        log.info(f"Creating settlements -- {settlements_gdb}")
        make_bld_contours.main(cfg)
        log.info("Closing process to unlock GDBs")
        return
    else:
        log.info(f"settlements already exist -- {settlements_gdb}")

    if not backup_settlements_gdb.exists():

        shutil.copytree(settlements_gdb, backup_settlements_gdb)
        log.info(f"Copying {settlements_gdb} to {backup_settlements_gdb}")

    if not backup_processing_gdb.exists():
        shutil.copytree(processing_gdb, backup_processing_gdb)
        log.info(f"Copying {processing_gdb} to {backup_processing_gdb}")

    class Messenger(object):
        def addMessage(self, message):
            log.info(message)

    clean = True
    if clean:
        if processing_gdb.exists():
            log.info(f"Removing {processing_gdb}")
            shutil.rmtree(processing_gdb)

        if settlements_gdb.exists():
            log.info(f"Removing {settlements_gdb}")
            shutil.rmtree(settlements_gdb)

        log.info(f"Copying {backup_settlements_gdb} to {settlements_gdb}")
        shutil.copytree(backup_settlements_gdb, settlements_gdb)

        log.info(f"Copying {backup_processing_gdb} to {processing_gdb}")
        shutil.copytree(backup_processing_gdb, processing_gdb)

        for pickle_file in Path(gi.GDB_PARENT_DIR).glob("*.pickle"):
            log.info(f'Removing {pickle_file}')
            pickle_file.unlink()


    show_fgdb_counts(settlements_gdb)
    show_fgdb_counts(processing_gdb)
    make_hamlet_areas_and_extend_buas.aggregate_buildings(Messenger(), cfg)
    show_fgdb_counts(settlements_gdb)
    #show_fgdb_counts(processing_gdb)

    import arcpy
    bua_non_extended_path = str(settlements_gdb / "bua_non_extended")
    bua_non_extended_count = int(arcpy.GetCount_management(bua_non_extended_path)[0])

    assert bua_non_extended_count == 1

def show_fgdb_counts(fgdb_path):

    if not fgdb_path.exists():
        log.info(f"{fgdb_path} does not exist")
        return


    log.info("\n\n")
    log.info(f"Counts for {fgdb_path}")

    from osgeo import ogr
    conn = ogr.Open(str(fgdb_path))

    if not conn:
        log.warning(f"Connection is None/blank for {fgdb_path}")
        return

    for featsClass_idx in range(conn.GetLayerCount()):
        featsClass = conn.GetLayerByIndex(featsClass_idx)
        name = featsClass.GetName()
        count = featsClass.GetFeatureCount()
        log.info(f"{name} has {count} rows")

    log.info("\n\n")
def main():
    init_logging(True)
    log.info("test")
    run_test(test3())

if __name__ == "__main__":
    main()