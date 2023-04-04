# Main POI processing scripts

## Config file

- **POI_process_config.ini.template** the template that holdes all of the variables used in the POI processing scripts. 
  - A copy of this file should be created and named POI_processing_config.ini
  - Variables for each line should be updated with information for the POI you are processing
  - The same config file is currently used for all scripts in this directory (this can change)

## Cleaning and EDA

- **preprocessing1_pipeline** This script cleans POI names by utilizing the type and spelling dictionaries. The POI_processing_config.ini must be compleated and reside in the same directory as this script

- **preprocessing2_pipeline** Preprocessing2 uses the output of preprocessing 1 along with boundary and settlement extents to evaluate the quality of the points of interest. It also cleans and matches admin level data.

- **Create long/short explority report** R scripts used to generate exploritory data analysis reports. it uses the output of prepressing2 along with boundaries to create maps and graphs

## Creating spelling and type dictionaries

- **word_frequency_table_pipline** First script run agains the POI names to find repeated words that represent types. The output needs to be cleaned by hand to remove words that are not types of POI's but are often repeated such as the word "Saint". 

- **type_dictionary_pipeline** Using the cleaned word frequency output this script creates a type dictionary. The output needs to be cleaned by hand to remove or consolidate poi types

- **spelling_dictionary_pipeline** Using the cleaned output of the type dictionary this script creates a list of misspelled words. The output needs to be cleaned by hand to remove words added in error such as "Saint" seen as a misspelling for "Sante"

## Cleaning duplicate POI's

- **Optimization_pipeline** Script used to find the best geolocated point when multiple points for the same POI exists.
- **Optimization_utilities** Main code base used in the optimization pipeline


# Word Frequency

## Objective
Usually facilty names and types are written together in the 'facility name' column in a health facility table. For example, "Makala Health Centre". "Makala" is the facility name and "Health Centre" is the type of facility. We need to separate facility name and facility type and put them into two different columns. In order to do that we need to know which words refer to the type of a facility.

## Process
This is a python notebook that runs on google cloud. A python notebook consists of cells that include python scripts. Each cell can be run individually. In order to run a cell, first click/hover on the cell. After the click, you should see an arrow at the left side of the cell. Click on the arrow to run the cell. The cells need to be run top to bottom.
This work consists of four steps.

#### Step 1:
* Create a word frequency table: A word frequency table will be generated after you run this notebook properly. The word frequency table contains words and how many times they are repeated in a dataset.
#### Step 2:
* Go through each word in the word frequency table: Open the word frequency table and keep only the words that refer to a facility type such as Centre, Clinic, Hospital, Health, HC, DISP, PHC .... Basically, you should delete all the words that refer to a facility name.
#### Step 3:
* Repeat steps 1 and 2 for each health facility dataset you have explored in previous landscaping exercises
#### Step 4:
* Combine all the word frequency tables that you created for each health facility dataset into one excel file. Upload that file to your country's Health Facilities dataset folder in the google drive.


# Create Type Dictionaties

## Objective
Creating a list of types of health facilities from facility names in a health facility dataset.

## Process

#### Step 1:
* Make a copy of this script and add the name of your country, e.g. type_dictionaries_MOZ. Then, create a facility type table: A facility type will be generated after you run this notebook properly.
#### Step 2:
* Go through each facility type in the facility type table: Check facility types in the generated facility table table, and make correcitons if facility types have any spelling issues. Some of the facility types are abbrivated. Write full name of abbrivated facility names.For example write HC *as *Health Center .The facility type table will also have an "abbreviation" column. Please fill the abbreviation column with the abbreviation of the facility type. For example, if the facility type is Health Center, the abbreviation should be HC.
#### Step 3:
* Repeat steps 1 and 2 for each health facility dataset you have explored in previous landscaping exercises
#### Step 4:
* Combine all the facility type tables that you created for each health facility dataset into one excel file. Upload that file to your country's Dictionaries folder in the google drive.


# Create Spelling Dictionaries

## Objective
Creating a list of misspellings in health facility types as extracted from from facility names in a health facility dataset.

## Process

#### Step 1:
* Make a copy of this script and add the name of your country, e.g. spelling_dictionaries_MOZ. Then, create a table with misspelled health facility type: This table will be generated after you run this notebook properly.
#### Step 2:
* Go through each misspelled name in the misspelled type table: We will use a misspelled type table in the next step to fix misspeling in some words. For example, we will convert all "hooital,hodpital,hopitap,hodpital" to "hospital". However, in some cases, some words that we find misspelled may not be wrong. For example, assume that this notebook finds that "sainte" should be spelled as "sante" (French for 'health') because they are very similar, but this assumption is not accurate. 'Sainte' could refer to 'Saint' (e.g. Sainte Marie) which is part of the facility name, not type. We should not convert 'sainte' to 'sante'. You should find these cases and delete them from the misspelled type table.
#### Step 3:
* Repeat steps 1 and 2 for each health facility dataset you have explored in previous landscaping exercises
#### Step 4:
* Combine all the misspelled type table that you created for each health facility dataset into one excel file. Upload that file to your country's Dictionaries folder in the google drive.


# Pre-Processing

## Objective
* Clean facility name (remove special characters, capitalize letters, convert roman numerals ...)
* Correct misspelling with help of spelling dictionary
* Separate facility name and facility type into separate columns with help of type dictionary
* Create facility sub-types

## Process

#### Step 1:
Make a copy of this script and add the name of your country to the file name, e.g. preprocessing_MOZ. Then, run this notebook on your health facility datasets. Doing so will add the following columns to your health facility datasets:
* facility_name_short: Cleaned facility names without a type. An example entry is 'Columbia,' which has been converted from 'columbia hospital.'
* extract_type :These are raw facility types extracted from facility_name column.
* sub_type : Formatted and aggregated facility type from extract_type column. The type dictionary is going to be used as reference facility types. In some countries, some facilities are written as District Hospital, and some of them as Hospital District. The extract_type column is going to hold both types, but in sub_type we will just keep District Hospital (based on type dictionary) as it is but reformat Hospital District as District Hospital.
* score : We are using a fuzzy match method to aggregate and format facility types from the extract_type column. This column shows the match score, which is a number 100-0. 100 indicates a perfect match, and 0 indicates that the values are totally different.
* hf_name_length : Length of facility name.
* hf_type_length : Length of facility type.
* special_chrs : List of special characters that a facility name includes such as !?/`"&*
* only_numerical : Facility names that consist of only numerical values
#### Step 2:
* Go through each facility type in the sub_type column that has a score lower than 75. We want to make sure we aggregate facility types in the right way. A score lower than 75 can be misclassified. Correct the cases that you find missclassified in the sub_type column.
* Check facilities without a type. Some of the facilites do not have a type. For those facilities, the sub_type column should be empty. For these cases, check the facility_name_short column and confirm facility name does not include a type. If you find that facility name includes its type, manually exclude facility type from facility name in facility_name_short column and move facility type to sub_type column.
* Check facilities without a name. Some of the facilities do not have a name. For those cases facility_name_short should be empty. If it's empty, check facility_name column and confirm that the facility name does not include a name (just type). If you find that, in the facility_name column, a facility name exists, manually enter facility name into facility_name_short column.
* Check very long or short facility name. Some facility names are very long or short. Sometimes that's an indication that the name is wrong, so we need to manually check. Please go over facility names in facility_name_short column that have over 30 characters and less than 3 characters. You can sort text by length in Excel. Correct facility name in facility_name_short column if you think they are misspelled.
* Check very long or short facility types: Some of the facility types are very long or short. Please go over facility types in sub_type that have over 20 characters and fewer than 3 characters. Correct facility type at sub_type if you think they are misspelled.
* Check facility names that have a special characters. Facility names that have special characters have been palced in a special_chrs column.Some of these characters are not right.Remove the characters at facility_name_short column that are listed special_chrs column that you think wrong.
* Check facility names that consist of only numerical characters. These facilities are flagged in an only_numerical column. For these cases, check facility_name column name, and confirm that facility name consists of only numerical values. If not, correct the facility name in the facility_name_short column.
#### Step 3:
* Repeat steps 1 and 2 for each health facility dataset you have explored in previous landscaping exercises.

