# Script Name: 3_mod_transit.py
# Author: Mark Egge & Josh Reynolds
# Created: 2025-05-22

import sys
if not "edit" in sys.argv:
    print('--begin mod transit' )

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
    filename='logs/3_mod_transit.log',  # Log to a file (optional)
    filemode='a'  # Append to the file (use 'w' to overwrite)
)

if not "edit" in sys.argv:
    logging.info("begin mod transit")

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    
config = load_yaml('src/0_config.yaml')
arcgis_pro = config['arcgis_pro']   

base_path = os.path.abspath(".")
aprx_path = os.path.realpath("ato.aprx")

# store values from user entry
global entry_value
global combo_value

if len(sys.argv) < 3:
    print("Error: Missing arguments. Provide both entry and combobox values.")
    logging.error("Missing arguments. Provide both entry and combobox values")
    sys.exit(1)
else:
    entry_value = sys.argv[1]
    combo_value = sys.argv[2]    

mode = "Transit"
target_gdb =  os.path.join(base_path, "scenario", mode, entry_value + ".gdb")
layer_name = 'BPA-Scenario'

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

    # # Add BikePedAuto layer to map for editing
    # layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"))
    # layer.name = layer_name

    # Add Transit layers to map for editing
    bpa_layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"))
    bpa_layer.visible = False

    transit_routes_layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\TransitRoutes"))
    transit_stops_layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\TransitStops"))
    connector_network_layer = map_obj.addDataFromPath(os.path.join(target_gdb, r"NetworkDataset\ConnectorNetwork"))

    
    # save and remove the project from the namespace
    aprx.save()
    del aprx, map_obj
    logging.info("ArcGIS Pro project closed")
    time.sleep(10)

    # Restart the script in a new process so that any locks are released 
    logging.info("Restarting the mod transit script")
    subprocess.Popen([sys.executable, '-u'] + sys.argv + ["edit"], close_fds=True)

    # Exit the current script to ensure it stops completely
    sys.exit()


#======================
# modify  network
#======================

'''
**Follow the instructions below for the appropriate section to make edits**

### Improvements Table

Project Type (new and upgrades)|Action
---- | ----
Bus rapid transit (line)|Add line (new) or change route type & increase speed (upgrade)
Commuter rail (line) - extension|(probably evaluated in regional TDM)
Core route (line)|Add line (new)
Light rail (line)|Add line (new)
Street car (line)|Add line (new)

Ignoring for now: Park & Ride, Infill Station

## New Route

1. Add new feature to TransitRoutes Layer (i.e. Copy --> Paste Special)
2. Create new stops as required. Make sure that vertex points are coincident between a) the BikePedAuto layer; b) the TransitRoutes layer; and c) the TransitStops layer. This layer connectivity (connected by coincident vertices and TransitStop features) is essential for the correct function of Network Analyst.
3. Ensure that geometry precisely connects to stops or the ConnectorNetwork. Zoom way in. Move or create vertices as necessary.
4. With the new feature selected, run the Service Upgrade cell below to set travel times.

## Service Upgrade

1. Select affected feature (ideally by using "Select by Location" and select "within" segments), uncomment the appropriate speed in the cell below, and run

(Alternatively, for service upgrades on new fixed routes, follow the steps above for New Route)
 '''

def modify_network():

    # launch arcgis pro
    print('--launching ArcGIS Pro...')
    logging.info("launching ArcGIS Pro")
    print('--Remember to save the edits, leave the new/edited features selected, and save the project')
    try:
        subprocess.run([arcgis_pro, aprx_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to open ArcGIS Pro: {e}", "error")
        logging.error("Failed to open ArcGIS Pro")
        return
    

    #================================
    # resume after arcgis pro closes
    #================================

    print('--ArcGIS Pro session closed, resuming script')
    logging.info("ArcGIS Pro session closed, resuming script")
    # bpa = arcpy.management.MakeFeatureLayer(  os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"),  "BPA")

    # Open the ArcGIS Pro project
    logging.info("Accessing the ArcGIS Pro project")
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    m = aprx.listMaps(map_name)[0]
    bpa_layer = None
    transit_routes_layer = None
    transit_stops_layer = None
    connector_network_layer = None

    for lyr in m.listLayers():
        if lyr.name == "BikePedAuto":  
            bpa_layer = lyr
        if lyr.name == "TransitRoutes":  
            transit_routes_layer = lyr
        if lyr.name == "TransitStops":  
            transit_stops_layer = lyr
        if lyr.name == "ConnectorNetwork":  
            connector_network_layer = lyr
    
    print(f'--(re)calculating attributes for {combo_value}')
    logging.info(f"(re)calculating attributes for {combo_value}")

    operating_speeds = {
    "brt": config['transit_operating_speeds']['brt'],
    "commuter_rail": config['transit_operating_speeds']['commuter_rail'],
    "core": config['transit_operating_speeds']['core'], 
    "express": config['transit_operating_speeds']['express'],
    "light_rail": config['transit_operating_speeds']['light_rail'],
    "local": config['transit_operating_speeds']['local'],
    "street_car": config['transit_operating_speeds']['street_car']
    }
    

    '''For new construction, new lines and connections are added to the BPA-Scenario (BikePedAuto) layer in the Network Dataset.'''

    # UPDATE TransitTime FOR SELECTED FEATURES
    # SELECT ONLY AFFECTED FEATURES TO KEEP RUN TIME REASONABLE

    expression = '!Length_Miles! * 60 / ' + str(operating_speeds[combo_value])

    if 0 < int(arcpy.management.GetCount(transit_routes_layer)[0]) < 100:
        arcpy.management.CalculateField(
            transit_routes_layer,
            "Length_Miles", '!Shape_Length! * 0.000621371', "PYTHON3", 
            None, "DOUBLE"
        )
        arcpy.management.CalculateField(
            transit_routes_layer, "TransitTime", expression, "PYTHON3", None, "DOUBLE"
        )
    else:
        print("Warning: operation will affect " + 
            arcpy.management.GetCount(transit_routes_layer)[0] + 
            " features - did you select only the intended target?")
    

    # clear the selection before creating the new network dataset
    arcpy.management.SelectLayerByAttribute(bpa_layer, "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(transit_routes_layer, "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(transit_stops_layer, "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(connector_network_layer, "CLEAR_SELECTION")

    # remove the layers and close the project
    m.removeLayer(bpa_layer)
    m.removeLayer(transit_routes_layer)
    m.removeLayer(transit_stops_layer)
    m.removeLayer(connector_network_layer)

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
    logging.info('mod drive completed')
    
if __name__ == "__main__":
    main()