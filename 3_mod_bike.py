
'''Network Modifications - Bikes
In this notebook a copy of our baseline NetworkDataset is made to be modified reflecting the candidate improvement for bicycle projects.

To use this notebook, set the scenario name and improvement type in the cell below. Then, run the first three cells, the appropriate cells for the improvement, and save your changes.'''


import sys
if not "edit" in sys.argv:
    print('--begin mod bike' )

import os
import arcpy
import shutil
import subprocess
import time
import yaml
import logging
from src.ato_tools import ato

arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "90%"

# set up logger
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    filename='logs/3_mod_bike.log',  # Log to a file (optional)
    filemode='a'  # Append to the file (use 'w' to overwrite)
)

if not "edit" in sys.argv:
    logging.info("begin mod bike")

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    
config = load_yaml('0_config.yaml')
arcgis_pro = config['arcgis_pro']
python = config['python']

base_path = os.path.abspath(".")
aprx_path = os.path.realpath("ato.aprx")

# get this from an argument in the gui
# scenario_name = "test_buffered_bike_lane" # e.g. "4700_south_bike_lane"
# facility_type = "buffered_bike_lane"

global entry_value
global combo_value

if len(sys.argv) < 3:
    print("Error: Missing arguments. Provide both entry and combobox values.")
    logging.error("Missing arguments. Provide both entry and combobox values")
    sys.exit(1)
else:
    entry_value = sys.argv[1]
    combo_value = sys.argv[2]

mode = "Cycling"
target_gdb =  os.path.join(base_path, "scenario", mode, entry_value + ".gdb")
layer_name = 'BPA'

#===========================
# prepare template network
#===========================

def  prepare_network():
    
    print('--preparing template network')
    logging.info("preparing template network")

    #-------------------------------------------------
    # create scenario file geodatabase from template
    #-------------------------------------------------

    # if target gdb exists, delete it
    if os.path.isdir(target_gdb):
        shutil.rmtree(target_gdb)
        
    # copy template
    shutil.copytree(r"scenario\scenario_template.gdb", target_gdb)
    arcpy.env.workspace = target_gdb

    # Open the ArcGIS Pro project
    logging.info("Accessing the ArcGIS Pro project")
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    map_obj = aprx.listMaps(map_name)[0]

    # clear layers
    layers_to_keep = ["World Topographic Map", "World Hillshade"]
    for lyr in reversed(map_obj.listLayers()):
        if lyr.name not in layers_to_keep:
            map_obj.removeLayer(lyr)

    # Add BikePedAuto layer to map for editing
    layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"))
    layer.name = layer_name

    # save and remove the project from the namespace
    aprx.save()
    del aprx, map_obj
    logging.info("ArcGIS Pro project closed")
    time.sleep(10)

    # Restart the script in a new process so that any locks are released 
    logging.info("Restarting the mod bike script")
    subprocess.Popen([python, '-u'] + sys.argv + ["edit"], close_fds=True)

    # Exit the current script to ensure it stops completely
    sys.exit()

#======================
# modify  network
#======================

def modify_network():

    # launch arcgis pro  
    print('--launching ArcGIS Pro...')
    logging.info("launching ArcGIS Pro")
    print('--Remember to save edits, leave new/edited features selected, and save the project')
    try:
        subprocess.run([arcgis_pro, aprx_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to open ArcGIS Pro: {e}", "error")
        logging.error("Failed to open ArcGIS Pro")
        return
    
    # Make Edits
    '''**Follow the instructions below for the appropriate section to make edits**

    When creating new (greenfield) bicycle facilities, add these to the BPA layer.

    When adding a bicycle improvement to an existing roadway (e.g. creating a bicycle boulevard) select the appropriate segments in the BPA layer. (Hint: use "Select by Location" and "Within")'''

    ## New Feature
    '''For new facilities (e.g. new shared use paths, etc.), create a new feature in the BPA layer corresponding to the new facility. Be sure to make there are overlapping vertices at intended connection points.'''


    #================================
    # resume after arcgis pro closes
    #================================

    print('--ArcGIS Pro session closed, resuming script')
    logging.info("ArcGIS Pro session closed, resuming script")
    bpa = arcpy.management.MakeFeatureLayer(  os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"),  "BPA")

    # Open the ArcGIS Pro project
    logging.info("Accessing the ArcGIS Pro project")
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    m = aprx.listMaps(map_name)[0]
    bpa = m.listLayers(layer_name)[0]

    # SET ATTRIBUTES FOR NEW FEATURE
    # Highlight new feature and run this cell
    print(f'--(re)calculating attributes for {combo_value}')
    logging.info(f"(re)calculating attributes for {combo_value}")

    if int(arcpy.management.GetCount(bpa)[0]) < 5:
        arcpy.management.CalculateField(bpa, "Name", "'" + entry_value + "'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "Length_Miles", '!shape.length@miles!', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "PedestrianTime", '!Length_Miles! / (3 / 60)', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "BikeTime", '!Length_Miles! / (11 / 60)', "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "AutoNetwork", "'N'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "BikeNetwork", "'Y'", "PYTHON3", None, "DOUBLE")
        arcpy.management.CalculateField(bpa, "PedNetwork", "'Y'", "PYTHON3", None, "DOUBLE")
    else:
        print("--Error: operation will affect more than 5 features. Did you select only the new bike facility(s)?")
        logging.warning(f"Error: operation will affect more than 5 features")

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
        multiplier = length_multipliers[combo_value]
        
        # for bike lanes, determine the max aadt. If > 10k, set mutiple to 0.9
        # rather than 0.3
        if combo_value == "bike_lane":
            max_aadt = max([row[0] for row in arcpy.da.SearchCursor(bpa, "AADT")])
            if max_aadt > 15000:
                print('--Maximum AADT is {}. Length multiple set to 0.9'.format(max_aadt))
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
        print(f"--Warning: operation will affect {arcpy.management.GetCount(bpa)[0]} features - did you select only the intended target?")
        logging.warning(f"operation will affect {arcpy.management.GetCount(bpa)[0]} features")

    ## Save Edits

    # save edits (if any) to BPA layer using the Edit ribbon - first!

    # clear the selection before creating the new network dataset
    arcpy.management.SelectLayerByAttribute(bpa, "CLEAR_SELECTION")

    # remove the bpa layer and close the project
    m.removeLayer(bpa)
    aprx.save()
    del aprx
    logging.info("ArcGIS Pro project closed")
        

    # build the newly created network dataset
    print('--rebuilding the modified network')
    logging.info("rebuilding the modified network")
    nd = os.path.join(target_gdb, r"NetworkDataset\NetworkDataset_ND")
    arcpy.CheckOutExtension("Network")
    ato.build(nd)
    logging.info("modified network rebuilt")
    arcpy.CheckInExtension("Network")

    

###################
# MAIN
###################
def main():
    if "edit" in sys.argv:
        logging.info('modify network started')
        modify_network()
        logging.info('modify network completed')
    else:
        logging.info('prepare network started')
        prepare_network()
        logging.info('prepare network completed')
    logging.info('mod bike completed')
    
if __name__ == "__main__":
    main()



