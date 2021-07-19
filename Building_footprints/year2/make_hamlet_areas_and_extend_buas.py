import os

import arcpy
import pickle 
from pathlib import Path
from config import Config as cfg

from config import Config


def aggregate_buildings(messages, cfg: Config):
    # ------------------ PARAMS To play With -----------------------

    # radius
    HAMLET_BUFFER_SIZE = 25
    HA_BUFFER_SIZE = 100
    BATCH_SIZE = 300000

    RESET = False
    BUA_BEND_TOLERANCE = 2000  # in meters
    BUA_BENDED_BUFFER_SIZE = 500  # in meters

    SSA_BEND_TOLERANCE = 2000  # in meters
    SSA_BENDED_BUFFER_SIZE = 500  # in meters
    # ------------------ END PARAMS To play With -------------------
    counts = {
        'building': 0,
        'split_table': 0
    }

    out_gdb_path = os.path.join(cfg.GDB_INFO.GDB_PARENT_DIR, cfg.GDB_INFO.OUTPUT_GDB_NAME)
    work_gdb_path = os.path.join(cfg.GDB_INFO.GDB_PARENT_DIR, cfg.GDB_INFO.WORK_GDB_NAME)


    tmp_buffer = os.path.join(work_gdb_path, "tmp_buffer")
    tmp_merged = os.path.join(work_gdb_path, "tmp_merged")
    tmp_dissolved = os.path.join(work_gdb_path, "tmp_dissolved")

    tmp_bua_fc = os.path.join(work_gdb_path, "tmp_bua")
    tmp_ssa_fc = os.path.join(work_gdb_path, "tmp_ssa")
    tmp_hamlet_fc = os.path.join(work_gdb_path, "tmp_hamlet")
    tmp_ha_fc = os.path.join(work_gdb_path, "tmp_ha")
    tmp_ha_fc_no_ssa = os.path.join(work_gdb_path, "tmp_ha_no_ssa")

    # Phase I output 
    bua_fc = os.path.join(out_gdb_path, "bua_non_extended")
    ssa_fc = os.path.join(out_gdb_path, "ssa_non_extended")

    # Phase II output 
    bua_output_fc = os.path.join(out_gdb_path, "bua")
    ssa_output_fc = os.path.join(out_gdb_path, "ssa")

    ha_fc = os.path.join(out_gdb_path, "ha")

    hamlet_fc = os.path.join(out_gdb_path, "hamlet")
    tmp_bended_bua_fc = os.path.join(work_gdb_path, "tmp_bended_bua_fc")
    tmp_tmp_bua_mask_fc = os.path.join(work_gdb_path, "tmp_tmp_bua_mask_fc")
    tmp_bua_mask_fc = os.path.join(work_gdb_path, "tmp_bua_mask_fc")

    tmp_bended_ssa_fc = os.path.join(work_gdb_path, "tmp_bended_ssa_fc")
    tmp_tmp_ssa_mask_fc = os.path.join(work_gdb_path, "tmp_tmp_ssa_mask_fc")
    tmp_ssa_mask_fc = os.path.join(work_gdb_path, "tmp_ssa_mask_fc")

    def prepare_workspace():
        """
        Prepares the workspace
        :return:
        """
        # if RESET and arcpy.Exists(out_gdb_path):
            # arcpy.Delete_management(out_gdb_path)

        # if not arcpy.Exists(os.path.join(output_folder, "settlements.gdb")):
            # arcpy.CreateFileGDB_management(output_folder, "settlements.gdb")

        arcpy.env.workspace = out_gdb_path
        
        if not arcpy.Exists(work_gdb_path):
            os.makedirs(cfg.GDB_INFO.GDB_PARENT_DIR, exist_ok=True)
        
            arcpy.CreateFileGDB_management(
                cfg.GDB_INFO.GDB_PARENT_DIR,
                cfg.GDB_INFO.WORK_GDB_NAME)

    def calculate_area(input_fc, fieldname):
        """
        Calculates the footprints area in km2
        :return:
        """
        if len(arcpy.ListFields(input_fc, fieldname)) <= 0:
            arcpy.AddField_management(input_fc, fieldname, "FLOAT")
            arcpy.CalculateField_management(in_table=input_fc, field=fieldname,
                                            expression="!Shape.area@SQUAREKILOMETERS!", expression_type="PYTHON_9.3",
                                            code_block="")

    def log_percentage(i, last_log, message):
        """
        Logs percentage advancement on a task
        :param i:
        :param last_log:
        :param message:
        :return:
        """
        denom = (counts['split_table'] - 1)
        if denom <= 0:
            denom = 1
        perc = (i * 100) // denom
        value = last_log
        while value <= perc and value <= 100:
            value = value + 10
        new_log = value - 10
        if new_log > last_log:
            messages.addMessage("{}: {}%".format(message, new_log))
            return new_log
        else:
            return last_log

    def split_table(table_to_split, table_prefix="T", reset=False, batch_size=BATCH_SIZE):
        """
        Splits the given table into several table based on a calculated attribute

        """
        
        arcpy.env.workspace = out_gdb_path
        
        counts['building'] = int(arcpy.GetCount_management(table_to_split)[0])
        counts['split_table'] = (counts['building'] // batch_size) + 1
        messages.addMessage(
            "\tSplitting table: {}, Feature count: {}, nbSplitTable: {}".format(table_to_split, counts['building'],
        
                                                                        counts['split_table']))

        last_split_exists = arcpy.Exists(os.path.join(work_gdb_path, f"{table_prefix}{counts['split_table'] - 1}"))
        
        should_reset = reset or RESET or not last_split_exists
        
        if should_reset:
            for i in range(counts['split_table']):
                split_tbl = os.path.join(work_gdb_path, f"{table_prefix}{i}".format(i))
                if arcpy.Exists(split_tbl):
                    messages.addMessage(f"Reset..removing {split_tbl}")
                    arcpy.Delete_management(split_tbl)
                split_tbl = os.path.join(work_gdb_path, f"T{i}".format(i))
                if arcpy.Exists(split_tbl):
                    messages.addMessage(f"Reset..removing {split_tbl}")
                    arcpy.Delete_management(split_tbl)

        should_recalculate = (should_reset or len(arcpy.ListFields(table_to_split, "seq_nr")) <= 0)
        if len(arcpy.ListFields(table_to_split, "seq_nr")) <= 0:
            arcpy.AddField_management(table_to_split, "seq_nr", "LONG")
        if should_recalculate:
            arcpy.CalculateField_management(in_table=table_to_split, field="seq_nr",
                                            expression="autoIncrement()", expression_type="PYTHON_9.3",
                                            code_block="""rec=0 
def autoIncrement(): 
    global rec 
    pStart = 1  
    pInterval = 1 
    if (rec == 0):  
        rec = pStart  
    else:  
        rec += pInterval  
    return rec//{}""".format(batch_size))

        if should_reset:
            messages.addMessage(f"\tSplit by Attribute input-{table_to_split} workspace-{work_gdb_path}")
            arcpy.SplitByAttributes_analysis(
                Input_Table=table_to_split, 
                Target_Workspace=work_gdb_path,
                Split_Fields="seq_nr")
                                             
        
            if table_prefix != "T":
                for i in range(counts['split_table']):
                    created_split_tbl = os.path.join(work_gdb_path, f"T{i}".format(i))
                    renamed_split_tbl = os.path.join(work_gdb_path, f"{table_prefix}{i}".format(i))
                    arcpy.Rename_management(created_split_tbl, renamed_split_tbl)
                
        messages.addMessage("\tSplit -> OK")
        
        arcpy.env.workspace = out_gdb_path

    def generate_hamlet_areas():
        """
        Generate HAs
        :return:
        """
        ha_lyr = "ha_lyr"
        
        if arcpy.Exists(ha_fc):
            messages.addMessage(f"\tHamlet areas already exist {ha_fc}, returning...")
            return
        
        messages.addMessage("\tClustering hamlets at {}m...".format(HA_BUFFER_SIZE))

        # delete_split_table()
        split_table_prefix = "ha_split_"
        split_table(hamlet_fc, table_prefix=split_table_prefix, reset=False,)
        messages.addMessage("Generating Hamlet Areas...split complete")

        last_log = 0
        batch_list = []
        for i in range(0, counts['split_table']):
            base_split = os.path.join(work_gdb_path, f"{split_table_prefix}{i}")
            buffer_table = "{}_buff".format(base_split)
            dissolve_table = "{}_dissolve".format(base_split)
            with_stats_table = f"{base_split}_with_stats"

            if not arcpy.Exists(buffer_table):
                messages.addMessage(
                    f"Generating Hamlet Areas...Buffer analysis with HA buffer size {HA_BUFFER_SIZE}m"
                    f" - hamlet buffer size {HAMLET_BUFFER_SIZE}m")
                arcpy.gapro.CreateBuffers(input_layer=base_split,
                                          out_feature_class=buffer_table,
                                          method="PLANAR",
                                          buffer_type="DISTANCE",
                                          dissolve_option="NONE",
                                          multipart="SINGLE_PART",
                                          buffer_distance="{} Meters".format(HA_BUFFER_SIZE - HAMLET_BUFFER_SIZE)
                                          )

            if not arcpy.Exists(dissolve_table):
                messages.addMessage("Generating Hamlet Areas...Dissolve_management")
                # failed with ERROR 001409: Failed to write to the output location.
                # arcpy.gapro.DissolveBoundaries(
                #     input_layer=buffer_table,
                #     out_feature_class=dissolve_table,
                #     multipart="SINGLE_PART",
                #     dissolve_fields="NO_DISSOLVE_FIELDS",
                # )
                arcpy.Dissolve_management(in_features=buffer_table,
                                          out_feature_class=dissolve_table,
                                          multi_part="SINGLE_PART",

                                          )

            if not arcpy.Exists(with_stats_table):

                # arcpy.SummarizeWithin_analysis(
                #     in_polygons=dissolve_table, in_sum_features=base_split,
                #     out_feature_class= with_stats_table,
                #     keep_all_polygons="KEEP_ALL",
                #                             sum_fields = [
                #     ['bld_count', 'SUM'],
                #      ['sum_bld_area', 'SUM'],
                #      ['min_bld_area', 'MIN'],
                #      ['max_bld_area', 'MAX'],
                #                  ], sum_shape="NO_SHAPE_SUM" )

                arcpy.gapro.SummarizeWithin(
                    summarized_layer=base_split,
                    out_feature_class=with_stats_table,
                    polygon_or_bin="POLYGON",
                    #bin_type="SQUARE",
                    summary_polygons=dissolve_table,
                    sum_shape="NO_SUMMARY",
                    standard_summary_fields=[
                        ['bld_count', 'SUM'],
                        ['SUM_bld_area', 'SUM'],
                        ['MIN_bld_area', 'MIN'],
                        ['MAX_bld_area', 'MAX'],
                                     ],
                )

            batch_list.append(with_stats_table)
            last_log = log_percentage(i, last_log, "\t\tClustering {}m".format(HA_BUFFER_SIZE))

        messages.addMessage("\t\tMerging {}m cluster batches...".format(HA_BUFFER_SIZE))
        if not arcpy.Exists(tmp_merged):
            messages.addMessage(f"\t\tMerging {tmp_merged}..")
            arcpy.Merge_management(batch_list, tmp_merged)

            arcpy.AlterField_management(
                in_table=tmp_merged,
                field='COUNT',
                new_field_name='no_hamlets',
                new_field_alias='no_hamlets'
            )



        if not arcpy.Exists(tmp_dissolved):
            messages.addMessage(f"\t\tDissolving to {tmp_dissolved}..")
            arcpy.Dissolve_management(in_features=tmp_merged, out_feature_class=tmp_dissolved,
                                      multi_part="SINGLE_PART",
                                      )

        if not arcpy.Exists(tmp_ha_fc):
            messages.addMessage(f"\t\tCreating {tmp_ha_fc}..")
            # because the dissolve loses the stat fields, we put them back using this call.
            # the polyons are dissolved, the stats come from merged
            arcpy.gapro.SummarizeWithin(
                summarized_layer=tmp_merged,
                out_feature_class=tmp_ha_fc,
                polygon_or_bin="POLYGON",
                # bin_type="SQUARE",
                summary_polygons=tmp_dissolved,
                sum_shape="NO_SUMMARY",
                standard_summary_fields=[
                    ['SUM_bld_count', 'SUM'],
                    ['no_hamlets', 'SUM'],
                    ['SUM_SUM_bld_area', 'SUM'],
                    ['MIN_MIN_bld_area', 'MIN'],
                    ['MAX_MAX_bld_area', 'MAX'],
                ],
            )

            # we don't want the merged objectid field
            arcpy.DeleteField_management(in_table=tmp_ha_fc, drop_field=[
                "OBJECTID","COUNT"])


            arcpy.AlterField_management(
                in_table=tmp_ha_fc,
                field='MAX_MAX_MAX_bld_area',
                new_field_name='MAX_bld_area',
                new_field_alias='max_bld_area'
            )
            arcpy.AlterField_management(
                in_table=tmp_ha_fc,
                field='MIN_MIN_MIN_bld_area',
                new_field_name='MIN_bld_area',
                new_field_alias='min_bld_area'
            )
            arcpy.AlterField_management(
                in_table=tmp_ha_fc,
                field='SUM_SUM_SUM_bld_area',
                new_field_name='SUM_bld_area',
                new_field_alias='sum_bld_area'
            )

            # we want the data type to be Long instead of double
            arcpy.AddField_management(tmp_ha_fc, "bld_count", "LONG")
            arcpy.CalculateField_management(tmp_ha_fc, "bld_count", "!SUM_SUM_bld_count!", "PYTHON_9.3")
            arcpy.DeleteField_management(tmp_ha_fc, 'SUM_SUM_bld_count')

            arcpy.AddField_management(tmp_ha_fc, "no_hamlets", "LONG")
            arcpy.CalculateField_management(tmp_ha_fc, "no_hamlets", "!SUM_no_hamlets!", "PYTHON_9.3")
            arcpy.DeleteField_management(tmp_ha_fc, 'SUM_no_hamlets')



        if not arcpy.Exists(tmp_ha_fc_no_ssa):
            messages.addMessage(f"\t\tCreating {tmp_ha_fc_no_ssa} by removing any intersecting parts from SSAs...")

            # to fix some void geometry errors 
            arcpy.RepairGeometry_management(tmp_ha_fc)
            arcpy.RepairGeometry_management(ssa_fc)

            arcpy.Erase_analysis(in_features=tmp_ha_fc,
                                   erase_features=ssa_fc,
                                   out_feature_class=tmp_ha_fc_no_ssa,

                                   )                                   
           
            # Otherwise there can be issues with missing Hamlet Areas 
            messages.addMessage(f"Repair {tmp_ha_fc_no_ssa}...")
            arcpy.RepairGeometry_management(tmp_ha_fc_no_ssa)

        if not arcpy.Exists(ha_fc):
            
            messages.addMessage(f"\t\tCreating {ha_fc} by removing any intersecting parts from BUAs...")
            
            messages.addMessage(f"Repair {bua_fc}...")
            arcpy.RepairGeometry_management(bua_fc)
        
            messages.addMessage(f"Create {ha_fc}...")
            arcpy.Erase_analysis(in_features=tmp_ha_fc_no_ssa,
                                   erase_features=bua_fc,
                                   out_feature_class=ha_fc,
                                   )
                                   
            arcpy.CopyFeatures_management(ha_fc, ha_fc + "_orig")


    def bend_simplify_buas():
        """
        Simplify BUAs
        """
        if not arcpy.Exists(tmp_bended_bua_fc):
            messages.addMessage(f"Creating {tmp_bended_bua_fc}")
            
            bua_lyr = 'bua_lyr'
            arcpy.MakeFeatureLayer_management(bua_fc, bua_lyr)
            arcpy.SimplifyPolygon_cartography(in_features=bua_lyr,
                                              out_feature_class=tmp_bended_bua_fc,
                                              algorithm="BEND_SIMPLIFY",
                                              tolerance="{0} Meters".format(BUA_BEND_TOLERANCE),
                                              collapsed_point_option="NO_KEEP")
            arcpy.Delete_management(bua_lyr)

    def bend_simplify_ssas():
        """
        Simplify SSAs
        """
        if arcpy.Exists(tmp_bended_ssa_fc):
            messages.addMessage(f"\t\tAlready created simplified SSAs {tmp_bended_ssa_fc}..")
            return 
            
        split_table_prefix = "ssa_split_"
        split_table(ssa_fc, table_prefix=split_table_prefix, batch_size=2500, reset=False)
        
        batch_list = []
        
        for i in range(0, counts['split_table']):
            base_split = os.path.join(work_gdb_path, f"{split_table_prefix}{i}")
            ssa_lyr = f'ssa_lyr_{i}'
            out_fc = "{}_bent".format(base_split)
            
            batch_list.append(out_fc)
            
            # temp reset 
            if arcpy.Exists(out_fc):
                arcpy.Delete_management(out_fc)            
            
            if not arcpy.Exists(out_fc):
                row_count = int(arcpy.GetCount_management(base_split)[0])
                messages.addMessage(f"\t\tSimplifying {out_fc} from {base_split} / {ssa_lyr}..# of rows {row_count}")
                arcpy.MakeFeatureLayer_management(base_split, ssa_lyr)
                arcpy.SimplifyPolygon_cartography(in_features=ssa_lyr,
                                          out_feature_class=out_fc,
                                          algorithm="BEND_SIMPLIFY",
                                          tolerance="{0} Meters".format(SSA_BEND_TOLERANCE),
                                          collapsed_point_option="NO_KEEP")

        assert not arcpy.Exists(tmp_bended_ssa_fc)
        
        messages.addMessage(f"\t\tMerging {tmp_bended_ssa_fc}..")
        arcpy.Merge_management(batch_list, tmp_bended_ssa_fc)

    def generate_bua_masks():
        """
        Buffer and dissolve the simplified bended BUAs
        """
        if not arcpy.Exists(tmp_tmp_bua_mask_fc):
            # buffer
            bended_bua_lyr = 'bended_bua_lyr'
            arcpy.MakeFeatureLayer_management(tmp_bended_bua_fc, bended_bua_lyr)
            arcpy.Buffer_analysis(in_features=bended_bua_lyr,
                                  out_feature_class=tmp_tmp_bua_mask_fc,
                                  buffer_distance_or_field='{0} Meters'.format(BUA_BENDED_BUFFER_SIZE))

        if not arcpy.Exists(tmp_bua_mask_fc):
            # dissolve intersecting polygons
            tmp_tmp_bua_mask_lyr = 'tmp_tmp_bua_mask_lyr'
            arcpy.MakeFeatureLayer_management(tmp_tmp_bua_mask_fc, tmp_tmp_bua_mask_lyr)
            arcpy.Dissolve_management(in_features=tmp_tmp_bua_mask_lyr,
                                      out_feature_class=tmp_bua_mask_fc,
                                      multi_part='SINGLE_PART')


    def generate_ssa_masks():
        """
        Buffer and dissolve the simplified bended SSAs
        """
        if not arcpy.Exists(tmp_tmp_ssa_mask_fc):
            # buffer
            bended_ssa_lyr = 'bended_ssa_lyr'
            arcpy.MakeFeatureLayer_management(tmp_bended_ssa_fc, bended_ssa_lyr)
            arcpy.Buffer_analysis(in_features=bended_ssa_lyr,
                                  out_feature_class=tmp_tmp_ssa_mask_fc,
                                  buffer_distance_or_field='{0} Meters'.format(SSA_BENDED_BUFFER_SIZE))

        if not arcpy.Exists(tmp_ssa_mask_fc):
            # dissolve intersecting polygons
            tmp_tmp_ssa_mask_lyr = 'tmp_tmp_ssa_mask_lyr'
            arcpy.MakeFeatureLayer_management(tmp_tmp_ssa_mask_fc, tmp_tmp_ssa_mask_lyr)
            arcpy.Dissolve_management(in_features=tmp_tmp_ssa_mask_lyr,
                                      out_feature_class=tmp_ssa_mask_fc,
                                      multi_part='SINGLE_PART')


    def find_intersecting_multiple_masks(
            sett_fc,
            masks_lyr,
            label,
            tmp_mask_fc):
        """
        In certain particular cases, a BUA can intersect with multiple BUA masks.
        We need to find those in order to assign them to a single mask.
        :return Dict mapping OBJECTID of BUA or SSA to ObjectID of mask that has most overlap
        """
        settlement_to_max_mask = {}

        with arcpy.da.SearchCursor(sett_fc, ['SHAPE@', 'OBJECTID']) as settlements:

            if arcpy.Exists(masks_lyr):
                arcpy.Delete_management(masks_lyr) 

            arcpy.MakeFeatureLayer_management(tmp_mask_fc, masks_lyr)
            for sett in settlements:
                arcpy.SelectLayerByLocation_management(in_layer=masks_lyr,
                                                       overlap_type='INTERSECT',
                                                       select_features=sett[0])
                count = int(arcpy.GetCount_management(masks_lyr).getOutput(0))
                if count <= 1:
                    continue

                messages.addMessage(f'\t{label} {sett[1]} overlaps {count} masks')

                with arcpy.da.SearchCursor(masks_lyr, ['SHAPE@', 'OBJECTID']) as masks:

                    max_area = -1
                    for mask_row in masks:
                        mask_shape, mask_object_id = mask_row
                        mask_intersect_area = sett[0].intersect(mask_shape, 4).getArea()
                        messages.addMessage(f"Settlement {sett[1]} intersects mask {mask_object_id} by area {mask_intersect_area}")
                        if mask_intersect_area > max_area:
                            max_area = mask_intersect_area
                            settlement_to_max_mask[sett[1]] = mask_object_id

                    # select the mask that has the most area in common with the settlement
                    messages.addMessage(f"Setting settlement {sett[1]} to mask {settlement_to_max_mask[sett[1]]}")

        messages.addMessage(f'\tfound a total of {len(settlement_to_max_mask)} overlapping {label}s')

        return settlement_to_max_mask

    def add_required_fields():
        """
        Ensure expected fields are added (TODO why is this needed?)
        """
        #return

        for (field_name, field_type, field_length) in [
            ('bld_count', 'LONG', None),
            ('no_hamlets', 'LONG', None),
            ('mgrs_code', 'TEXT', 50),
            ('sum_bld_area', 'DOUBLE', None),
            ('sum_area', 'DOUBLE', None),
            ('type', 'TEXT', 16),
            # ('GlobalID', 'GUID', None, False)
        ]:
            for fc in [bua_output_fc, ssa_output_fc, ha_fc]:

                if len(arcpy.ListFields(fc, field_name)) <= 0:

                    arcpy.AddField_management(fc, field_name, field_type, field_length=field_length)

                    if field_name == "sum_area":
                        arcpy.CalculateGeometryAttributes_management(in_features=fc,
                                                                     geometry_property=[[field_name, "AREA_GEODESIC"]],
                                                                     area_unit="SQUARE_METERS")

        for fc in [ha_fc, ssa_output_fc, bua_output_fc]:
            # if fc == ha_fc:
            # arcpy.DeleteField_management(fc, ['GlobalID'])

            if len(arcpy.ListFields(fc, 'GlobalID')) <= 0:
                arcpy.AddGlobalIDs_management(fc)

    def add_intersecting_settlements(mask_lyr, settlement_lyr, satellite_settlement_lyr):

        satellite_label = satellite_settlement_lyr[:-4]
        settlement_label = settlement_lyr[:-4]

        # select intersecting area with Settlement masks
        messages.addMessage(f' *\tSelecting intersecting {satellite_label}/{satellite_settlement_lyr} ' +
            f'with {settlement_label}/{mask_lyr} masks')

        arcpy.SelectLayerByLocation_management(in_layer=satellite_settlement_lyr,
                                               overlap_type='INTERSECT',
                                               select_features=mask_lyr)
        # add them to the settlement feature class
        messages.addMessage(f'  \tAdding them to {settlement_label}s')
        arcpy.Append_management(inputs=satellite_settlement_lyr,
                                target=settlement_lyr)
        # remove them from feature class
        messages.addMessage(f'  \tRemoving them from {satellite_label}')
        arcpy.DeleteFeatures_management(satellite_settlement_lyr)

    def dissolve_settlements_in_masks(
            sett_lyr, 
            settlement_to_max_mask,
            mask_prefix,
            mask,
            label
            ) -> bool:
            
        mask_object_id = mask[1]
        
        # find intersecting settlements with current mask
        arcpy.SelectLayerByLocation_management(in_layer=sett_lyr,
                                               overlap_type='INTERSECT',
                                               select_features=mask[0])

        total_intersecting_setts = int(arcpy.GetCount_management(sett_lyr).getOutput(0))

        messages.addMessage(f' for {label} mask with id {mask_object_id}, '
                            f'# of intersecting settlements is {total_intersecting_setts}')

        if not total_intersecting_setts:
            return True 
        
        # filer out intersecting settlements that have a different maximum mask
        sett_filtered_out = tuple(filter(lambda sett_id: settlement_to_max_mask[sett_id] != mask_object_id,
                                         settlement_to_max_mask))
        if sett_filtered_out:
            messages.addMessage(f"Removing {len(sett_filtered_out)} settlements from selection of mask {mask_object_id} in {label}" )
            arcpy.SelectLayerByAttribute_management(in_layer_or_view=sett_lyr,
                                                    selection_type='REMOVE_FROM_SELECTION',
                                                    where_clause='OBJECTID IN ({})'.format(','.join(str(x) for x in sett_filtered_out)))

        total_filtered_intersecting_setts = int(arcpy.GetCount_management(sett_lyr).getOutput(0))

        messages.addMessage(f"For mask {mask_object_id}, we have {total_filtered_intersecting_setts} settlements")

        # if we have multiple settlements in the mask, dissolve them
        if total_filtered_intersecting_setts <= 1:
            return True 

        # MULTI_PART Dissolve
        tmp_dissolved_fc = os.path.join(work_gdb_path, f'{mask_prefix}_{mask[1]}')
        if not arcpy.Exists(tmp_dissolved_fc):
            messages.addMessage(f'Dissolving to {tmp_dissolved_fc} ')
            
            try: 
                arcpy.Dissolve_management(
                    in_features=sett_lyr,
                    statistics_fields=[
                      ['MAX_bld_area', 'MAX'],
                      ['MIN_bld_area', 'MIN'],
                      ['SUM_bld_area', 'SUM'],
                                     ['bld_count', 'SUM']],
                    out_feature_class=tmp_dissolved_fc,
                    multi_part='MULTI_PART')
            except Exception as ex:
                messages.addMessage(f"Exception caught {ex}\nRemoving {tmp_dissolved_fc}")
                # may exist in a bad state 
                if not arcpy.Exists(tmp_dissolved_fc):
                    arcpy.Delete_management(tmp_dissolved_fc)
                
                return False 
        else:
            messages.addMessage(f'{tmp_dissolved_fc} already exists, not recreating')

        # remove dissolved settlements from feature class
        arcpy.DeleteFeatures_management(sett_lyr)
        
        return True 

    def modify_areas_intersecting_bua_and_ssa_masks(clean=False):
        """
        1. Finds SSA and HA that intersects with the bended/simplified BUAs feature class.
           Changes those areas to BUA.
        2. Find BUAs that overlaps multiple masks and find their maximum overlapping area mask.
        3. Dissolve (MULTI_PART) BUAs inside a designated mask.
        """

        if clean and arcpy.Exists(ssa_output_fc):
            messages.addMessage(f"Cleaning delete {ssa_output_fc}")
            arcpy.Delete_management(ssa_output_fc)
        if clean and arcpy.Exists(bua_output_fc):
            messages.addMessage(f"Cleaning delete {bua_output_fc}")
            arcpy.Delete_management(bua_output_fc)

        if not arcpy.Exists(ssa_output_fc):
            arcpy.CopyFeatures_management(ssa_fc, ssa_output_fc)
        else:
            messages.addMessage(f' *\{ssa_output_fc} already exists, returing...')
            return

        if not arcpy.Exists(bua_output_fc):
            arcpy.CopyFeatures_management(bua_fc, bua_output_fc)
        else:
            messages.addMessage(f' *\{bua_output_fc} already exists, returing...')
            return

        bua_count = int(arcpy.GetCount_management(bua_output_fc)[0])

        add_required_fields()

        # field was added during the split, but we need the schemas to match exactly
        arcpy.DeleteField_management(ssa_output_fc, 'seq_nr')

        bua_lyr, ssa_lyr, ha_lyr = 'bua_lyr', 'ssa_lyr', 'ha_lyr'

        if not arcpy.Exists(bua_lyr):
            arcpy.MakeFeatureLayer_management(bua_output_fc, bua_lyr)
        if not arcpy.Exists(ssa_lyr):
            arcpy.MakeFeatureLayer_management(ssa_output_fc, ssa_lyr)
        if not arcpy.Exists(ha_lyr):
            arcpy.MakeFeatureLayer_management(ha_fc, ha_lyr)

        # 1. find and change SSA and HA intersecting BUA masks to BUA
        for lyr in (ssa_lyr, ha_lyr):
            if bua_count <= 0:
                messages.addMessage(f"No buas, so skipping add_intersecting_settlements")
                break

            add_intersecting_settlements(
                mask_lyr=tmp_bua_mask_fc,
                settlement_lyr=bua_output_fc,
                satellite_settlement_lyr=lyr
            )

        # 1b. Add intersecting HAs to SSAs.  We don't want to add BUAs since they were processed above
        # Also note, as HAs are already including hamlets, it does not make sense to include satellite settlements
        add_intersecting_settlements(
            mask_lyr=tmp_ssa_mask_fc,
            settlement_lyr=ssa_output_fc,
            satellite_settlement_lyr=ha_lyr
        )

        for is_bua in [True, False]:

            if is_bua and bua_count <= 0:
                messages.addMessage("No buas, skipping mask part")
                continue

            # set variables depending on if we are working on BUAs or SSAs.  This is to keep the code DRY
            if is_bua:
                sett_fc = bua_output_fc
                sett_lyr = bua_lyr
                masks_lyr = 'masks_bua_lyr'
                label = "BUA"
                tmp_mask_fc = tmp_bua_mask_fc
                mask_prefix = "tmp_bua_d_mp"
            else:
                sett_fc = ssa_output_fc
                sett_lyr = ssa_lyr
                masks_lyr = 'masks_ssa_lyr'
                label = "SSA"
                tmp_mask_fc = tmp_ssa_mask_fc
                mask_prefix = "tmp_ssa_d_mp"
            
            mask_pickle_file_path = Path(os.path.join(cfg.GDB_INFO.GDB_PARENT_DIR, f"ov_masks_{label}.pickle"))

            # 2. find overlapping BUA/SSAs and their maximum overlapping area mask
            messages.addMessage(f' *\tLooking for {label}s overlapping multiple masks')
            settlement_to_max_mask = {}  # A dict that maps an overlapping settlement object id with its most common area mask.

            # Load overlapping_objectids
            if mask_pickle_file_path.exists():
                messages.addMessage(f'find_intersecting_multiple_masks load pickle for {label}...')
            
                with open(mask_pickle_file_path, 'rb') as f:
                    settlement_to_max_mask = pickle.load(f)
            else:
                messages.addMessage(f'find_intersecting_multiple_masks for {label} calling...')
                
                settlement_to_max_mask = find_intersecting_multiple_masks(sett_fc,masks_lyr,label,tmp_mask_fc)
                
                with open(mask_pickle_file_path, 'wb') as f:
                    # Pickle the 'data' dictionary using the highest protocol available.
                    pickle.dump(settlement_to_max_mask, f, pickle.HIGHEST_PROTOCOL)

            # 3. Dissolve Settlements in masks
            with arcpy.da.SearchCursor(tmp_mask_fc, ['SHAPE@', 'OBJECTID']) as masks:
                messages.addMessage(f' *\tDissolving (MULTI_PART) {label}s in masks')
                for mask in masks:

                    for retry in range(0, 3):
                        ok = dissolve_settlements_in_masks(
                            sett_lyr,
                            settlement_to_max_mask,
                            mask_prefix,
                            mask,
                            label)
                        
                        if ok:
                            break
                    

            # append dissolved settlements back to the settlement feature class
            arcpy.env.workspace = work_gdb_path
            dissolved_tmp_feature_classes = arcpy.ListFeatureClasses(f'{mask_prefix}_*', feature_type='Polygon')
            if len(dissolved_tmp_feature_classes) > 0:
                messages.addMessage(f'  \tInserting {len(dissolved_tmp_feature_classes)} dissolved {label}s back to the {label} feature class')
                field_mappings = arcpy.FieldMappings()
                field_mappings.addTable(sett_fc)
                for nb, fc in enumerate(dissolved_tmp_feature_classes):
                    for att_prefix, attribute in zip(
                            ('SUM_', 'MIN_', 'MAX_', 'SUM_'),
                            ('SUM_bld_area', 'MIN_bld_area', 'MAX_bld_area', 'bld_count')):
                        # TODO instead of looping each time to find the attribute index, we could do it once
                        for i in range(field_mappings.fieldCount):
                            f = field_mappings.getFieldMap(i)
                            if attribute == f.getInputFieldName(0):
                                break
                        else:
                            raise Exception('Attribute "{}" was not found in the BUA feature class'.format(attribute))

                        f.addInputField(fc, f'{att_prefix}{attribute}')

                        field_mappings.replaceFieldMap(i, f)
                    messages.addMessage('  \t\tpreparing mapping for temp feature class {}/{}'.format(nb + 1, len(dissolved_tmp_feature_classes)))

                arcpy.Append_management(inputs=dissolved_tmp_feature_classes,
                                        target=sett_fc,
                                        field_mapping=field_mappings,
                                        schema_type='NO_TEST')
            else:
                messages.addMessage(f'  \tDid not found any dissolved {label}s to include in the {label} feature class')

        arcpy.DeleteField_management(ssa_output_fc, "no_hamlets")
        arcpy.DeleteField_management(bua_output_fc, "no_hamlets")

    def calculate_all_areas():

        for fc in [bua_output_fc, ssa_output_fc, ha_fc]:

            arcpy.CalculateGeometryAttributes_management(in_features=fc,
                                                         geometry_property=[['sum_area', "AREA_GEODESIC"]],
                                                         area_unit="SQUARE_METERS")

    def rename_final_layers():
        # for clarity, we rename the output of the previous script to "non extended" to indicate these are the layers before adding the satellite settlements
        
        if not arcpy.Exists(ssa_fc):
            messages.addMessage(f"Rename Phase I output ssa to {ssa_fc}")
            arcpy.Rename_management(os.path.join(out_gdb_path, "ssa"), ssa_fc)
            
        if not arcpy.Exists(bua_fc):
            messages.addMessage(f"Rename Phase I output bua to {bua_fc}")
            arcpy.Rename_management(os.path.join(out_gdb_path, "bua"), bua_fc)

    def main():
                
        messages.addMessage("Preparing ...")
        prepare_workspace()

        messages.addMessage("Renaming BUA and SSA to *_non_extended...")
        rename_final_layers()

        messages.addMessage("Simplifying (bend) BUAs...")
        bend_simplify_buas()

        messages.addMessage("Simplifying (bend) SSAs...")
        bend_simplify_ssas()


        messages.addMessage("Generating BUA masks...")
        generate_bua_masks()

        messages.addMessage("Generating SSA masks...")
        generate_ssa_masks()


        messages.addMessage("Generating Hamlet Areas...")
        generate_hamlet_areas()

        messages.addMessage("Changing settlements found inside BUA and SSAs masks to BUA and SSAs...")
        modify_areas_intersecting_bua_and_ssa_masks(clean=True)

        messages.addMessage("Calculating area field")
        calculate_all_areas()

        arcpy.Compact_management(out_gdb_path)

    main()


# =============================================================================
if __name__ == "__main__":
    # This is an example of how you could set up a unit test for this tool.
    # You can run this tool from a debugger or from the command line
    # to check it for errors before you try it in ArcGIS.
    class Messenger(object):
        def addMessage(self, message):
            print(message)


    # Run it.
    aggregate_buildings(Messenger(), Config())
