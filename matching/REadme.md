# Main Matching scripts

## Config file

- **matching_config.ini.template** the template that holdes all of the variables used in the POI processing scripts. 
  - A copy of this file should be created and named matching_config.ini
  - Variables for each line should be updated with information for the Input and Matching files
  - If both files have geospacial data you can match by distance by setting match_by_distance = True
  - The input file is missing some kind of data, the match file contains the data you want. For example the input data could be a MFL missing a lat and long and the matching file is a geospatial layer that contains the lat and long.

## Matching

- **Matching_pipeline** the main matching pipline that handels both matching by administrative levels and by distance.

- **Matching_utilities** the main code base used in the matching pipeline

- **Create_matching_report** an R script that creates a report describing the match results
