set PYTHON_EXE=C:\Users\jschmidt\AppData\Local\ESRI\conda\envs\grid3\python.exe
set SCRIPT_DIR=D:\GRID\year2
%PYTHON_EXE% %SCRIPT_DIR%\prep_building_footprints.py 
%PYTHON_EXE% %SCRIPT_DIR%\make_bld_raster.py 
%PYTHON_EXE% %SCRIPT_DIR%\make_bld_contours.py 
%PYTHON_EXE% %SCRIPT_DIR%\make_hamlet_areas_and_extend_buas.py 
%PYTHON_EXE% %SCRIPT_DIR%\make_bld_contours_open.py 
%PYTHON_EXE% %SCRIPT_DIR%\post_processing.py