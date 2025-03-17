
'''Network Modifications - Bikes
In this notebook a copy of our baseline NetworkDataset is made to be modified reflecting the candidate improvement for bicycle projects.

To use this notebook, set the scenario name and improvement type in the cell below. Then, run the first three cells, the appropriate cells for the improvement, and save your changes.'''

import sys
import os
import arcpy
import shutil
import subprocess
import time


base_path = os.path.abspath(".")
# src = os.path.join(base_path, 'src')
# if src not in sys.path:
#     sys.path.append(src)

from src.ato_tools import ato

aprx_path = os.path.realpath("ato.aprx")

# get this from an argument in the gui
scenario_name = "test_buffered_bike_lane" # e.g. "4700_south_bike_lane"
facility_type = "buffered_bike_lane"

mode = "Cycling"
target_gdb =  os.path.join(base_path, "scenario", mode, scenario_name + ".gdb")

#######################
# prepare bike network
#######################

def  prepare_bike_network():
    

    # create scenario file geodatabase from template

    # if target gdb exists, delete it
    if os.path.isdir(target_gdb):
        shutil.rmtree(target_gdb)
        
    # copy template
    shutil.copytree(r"scenario\scenario_template.gdb", target_gdb)

    arcpy.env.workspace = target_gdb

    #================================================
    # make sure this gets added to the pro project
    #================================================

    # Open the ArcGIS Pro project
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    m = aprx.listMaps(map_name)[0]
    layer = m.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"))
    layer.name = 'BPA'
    # Add BikePedAuto layer to map for editing

    aprx.save()
    # aprx  = None
    del aprx, m
    time.sleep(10)

    # Restart the script to zip the GDBs in a new process
    subprocess.Popen([sys.executable] + sys.argv + ["edit"], close_fds=True)

    # Exit the current script to ensure it stops completely
    sys.exit()

#######################
# modify bike network
#######################

def modify_bike_network():

    # launch arcgis pro
    print('opening arcgis pro...')
    print('Remember to save edits, leave new/edited features selected, and save project')
    subprocess.run([r"C:\Program Files\ArcGIS\Pro\bin\ArcGISPro.exe", aprx_path], check=True)
    
    # Make Edits
    '''**Follow the instructions below for the appropriate section to make edits**

    When creating new (greenfield) bicycle facilities, add these to the BPA layer.

    When adding a bicycle improvement to an existing roadway (e.g. creating a bicycle boulevard) select the appropriate segments in the BPA layer. (Hint: use "Select by Location" and "Within")'''

    ## New Feature
    '''For new facilities (e.g. new shared use paths, etc.), create a new feature in the BPA layer corresponding to the new facility. Be sure to make there are overlapping vertices at intended connection points.'''


    #================================
    # resume after arcgis pro closes
    #================================

    print('arcgis pro closed, resuming script')
    bpa = arcpy.management.MakeFeatureLayer(  os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"),  "BPA")

    # Open the ArcGIS Pro project
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    m = aprx.listMaps(map_name)[0]
    layer_name = "BPA"
    bpa = m.listLayers(layer_name)[0]

    # SET ATTRIBUTES FOR NEW FEATURE
    # Highlight new feature and run this cell
    if int(arcpy.management.GetCount(bpa)[0]) < 5:
        arcpy.management.CalculateField(bpa, "Name", "'" + scenario_name + "'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "Length_Miles", '!shape.length@miles!', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "PedestrianTime", '!Length_Miles! / (3 / 60)', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "BikeTime", '!Length_Miles! / (11 / 60)', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "AutoNetwork", "'N'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "BikeNetwork", "'Y'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "PedNetwork", "'Y'", "PYTHON3", None, "DOUBLE")
    else:
        print("Error: operation will affect more than 5 features. Did you select only the new bike facility(s)?")

    ## All Features (New & Existing)

    '''For new facilities AND to calculate updated attributes for adding bicycle facilities to existing roadways (e.g. adding a buffered bike lane), run the cell below.

    Select the relevent feature(s) (i.e. Select by Location where BPA features are _within_ the source feature) and run the cell below.'''

    length_multipliers = {
        "shared_lane": 1.0,
        "shoulder_bikeway": 0.5,
        "bike_lane": 0.5,
        "buffered_bike_lane": 0.3,
        "protected_bike_lane": 0.2,
        "bike_blvd": 0.1,
        "shared_use_path": 0.05
    }

    if int(arcpy.management.GetCount(bpa)[0]) < 50:
        multiplier = length_multipliers[facility_type]
        
        # for bike lanes, determine the max aadt. If > 10k, set mutiple to 0.9
        # rather than 0.3
        if facility_type == "bike_lane":
            max_aadt = max([row[0] for row in arcpy.da.SearchCursor(bpa, "AADT")])
            if max_aadt > 15000:
                print('Maximum AADT is {}. Length multiple set to 0.9'.format(max_aadt))
                multiplier = 0.9
        
        arcpy.management.CalculateField(
            bpa, "Length_Miles", 
            '!Length_Miles! * ' + str(multiplier), 
            "PYTHON3", None, "DOUBLE"
        )
        arcpy.management.CalculateField(
            bpa, "BikeTime", 
            '!Length_Miles! / (11 / 60)', 
            "PYTHON3", None, "DOUBLE"
        )


    else:
        print("Warning: operation will affect " + 
            arcpy.management.GetCount(bpa)[0] + 
            " features - did you select only the intended target?")

    ## Save Edits

    # save edits (if any) to BPA layer using the Edit ribbon - first!

    # clear the selection before creating the new network dataset
    try:
        arcpy.management.SelectLayerByAttribute(bpa, "CLEAR_SELECTION")
    except:
        pass

    # remove the bpa layer and close the project
    m.removeLayer(bpa)
    aprx.save()
    del aprx
        

    # Build the dataset
    nd = os.path.join(target_gdb, r"NetworkDataset\NetworkDataset_ND")
    arcpy.CheckOutExtension("Network")
    ato.build(nd)
    arcpy.CheckInExtension("Network")

    

###################
# MAIN
###################

if len(sys.argv) > 1 and sys.argv[1] == "edit":
    print('--begin editing')
    modify_bike_network()
    print('--scripts finished')
else:
    print('--begin prep script')
    prepare_bike_network()
    


#============================================================================
# add scenarios as many times as the user needs to (rerun/click the button)
#============================================================================



