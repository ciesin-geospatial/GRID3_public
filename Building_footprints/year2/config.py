import os


class ProcessedBuildingFootprints:
    """
    prep_building_footprints will process the input shapefiles and produce this GDB
    """

    def __init__(self, cfg):
        self.GDB_PARENT_DIR = fr'{cfg.GRID_HOME_DIR}\DIGITAL_GLOBE'
        self.GDB_NAME = fr'{cfg.COUNTRY_CODE}_y2.gdb'

        self.FEATURE_CLASS = "buildings"


class GDB_Info:
    """
    Processing GDB used by make_bld_raster & make_bld_contours to store intermediate feature classes
    """
    def __init__(self, cfg):
        self.GDB_PARENT_DIR = fr'{cfg.GRID_HOME_DIR}\Processed_y2'
        self.WORK_GDB_NAME = fr'{cfg.COUNTRY_CODE}_Processing_y2.gdb'

        self.OUTPUT_GDB_NAME = fr'{cfg.COUNTRY_CODE}_Settlements_y2.gdb'
        
        self.AGG_GDB_NAME = fr'{cfg.COUNTRY_CODE}_settlements_{cfg.RELEASE_DATE}_{cfg.CODE_VERSION}.gdb'
        
        self.EXT_GDB_NAME = fr'{cfg.COUNTRY_CODE}_settlement_extents_{cfg.RELEASE_DATE}_{cfg.CODE_VERSION}.gdb'
        
        self.OPEN_GDB_NAME = fr'GRID3_{cfg.COUNTRY_CODE}_settlement_extents_{cfg.RELEASE_DATE}_{cfg.CODE_VERSION}.gdb'

        # width of raster squares in meters, should match what the reference worldpop raster uses (see RASTER_GRID_PATH)
        self.RASTER_RESOLUTION = 100
        self.RASTER_NAME = fr'{cfg.COUNTRY_CODE}_{self.RASTER_RESOLUTION}'

        self.BUILDING_POINTS_FEATURE_CLASS = f"{cfg.COUNTRY_CODE}_blding_pnts"
        self.RASTER_POINTS_FEATURE_CLASS = f"{cfg.COUNTRY_CODE}_{self.RASTER_RESOLUTION}_rasterpnts"

class Config:

    def __init__(self):

        # This worldpop raster is used to snap the contours raster
        # https://www.worldpop.org/geodata/listing?id=59
        self.RASTER_GRID_PATH = os.environ["RASTER_GRID_PATH"]

        # Building footprint inputs
        self.BUILDING_FOOTPRINT_SHAPEFILE_PATHS = os.environ["BUILDING_FOOTPRINT_SHAPEFILE_PATHS"].split(";")

        self.COUNTRY_CODE = os.environ["COUNTRY_CODE"]
        
        self.RELEASE_DATE = os.environ["RELEASE_DATE"]
        
        self.CODE_VERSION = os.environ["CODE_VERSION"]

        self.GRID_HOME_DIR = fr'D:\GRID\{self.COUNTRY_CODE}'

        self.PROCESSED_BUILDING_FOOTPRINTS = ProcessedBuildingFootprints(self)

        self.GDB_INFO = GDB_Info(self)

