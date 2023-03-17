# GRID3_public
Opensource repository for grid3 projects


- **Dictionaries** Files to support the cleaning and standardization of data
- **POI_processing** Main set of pure python code for cleaning and exploring points of interest.
- **Utilities** Main shared code base for functions used in various pipelines

## Python Setup

### Installing Anaconda:


Download the installer from the anaconda website. An ad to buy the commercial version will pop up, but you can just close that.

https://www.anaconda.com/products/individual

The installer default options are all fine.
Install spyder or pycharm community
https://blog.jetbrains.com/pycharm/tag/community-edition/


### Installing Python in the Anaconda environment:


Open anaconda prompt -> Start -> Anaconda3 -> Anaconda Prompt


 The prompt will show your current directory.


Run the following commands, one at a time, to create a new Conda environment called geo_env

    conda create -n geo_env
    conda activate geo_env
    conda config --env --add channels conda-forge
    conda config --env --set channel_priority strict
    conda install python=3 geopandas
    conda install unidecode pointpats fuzzywuzzy configparser openpyxl rapidfuzz
    pip install ordered_set jellyfish
    
If you have an ssl issue see this

https://github.com/conda/conda/issues/11982


## Running pipelines :

All pipelines require a coresponding .ini file which specifies all our configuration.

Github includes a .ini.template file which specifies the paramaters needed, you should edit as needed. When saving, choose the save as type "all_files" and make sure the file name ends in .ini

The pipeline assumes a configuration file exists in the same directory with [pipeline-name].ini.  You can override this by running the pipeline with "-c path\to\config.ini"

### To ensure python can find your project you should add the GRID3 git repository to your PYTHONPATH.  

#### Using anaconda:

Assuming your code is in the directory is D:\git\GRID3

	1. launch the Anaconda Prompt
	
	activate geo_env
	
	2. run once:
	
	conda develop D:\git\GRID3

Example of running a matching_pipeline in windows with an optional config:

	1. launch the anaconda prompt
		activate geo_env
		d:
		cd git\GRID3
		python POI_processing\preprocessing1_pipline.py -c POI_processing\my_processing_config.ini
