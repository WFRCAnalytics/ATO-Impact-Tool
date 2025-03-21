
# Network Modifications - Roadways

'''In this notebook a copy of our baseline NetworkDataset is made to be modified reflecting the candidate improvement for roadway projects.

"E:\\Projects\\ATO-Impact-Tool\\3_mod_bike.ipynb"To use this notebook, modify the scenario name (below--no spaces or special characters) and run the three cells below, then run the approiate cell or cells under the "make edits" section corresponding to the project scope of work. Finally, run the cells at the bottom to save your work.'''



import sys
if not "edit" in sys.argv:
    print('--begin mod drive' )

import os
import arcpy
import shutil
import subprocess
import time
import yaml
from src.ato_tools import ato

arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "90%"

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

base_path = os.path.abspath(".")
aprx_path = os.path.realpath("ato.aprx")

# store values from user entry
global entry_value
global combo_value
if len(sys.argv) < 3:
    print("Error: Missing arguments. Provide both entry and combobox values.")
    sys.exit(1)
else:
    entry_value = sys.argv[1]
    combo_value = sys.argv[2]    

mode = "Driving"
# scenario_name = "central_bridge"
target_gdb =  os.path.join(base_path, "scenario", mode, entry_value + ".gdb")
layer_name = 'BPA-Scenario'

#######################
# prepare template network
#######################

def  prepare_network():

    print('--preparing template network')

    # create scenario file geodatabase from template

    # if target gdb exists, delete it
    if os.path.isdir(target_gdb):
        shutil.rmtree(target_gdb)
    
    # copy template
    shutil.copytree(r"scenario\scenario_template.gdb", target_gdb)

    arcpy.env.workspace = target_gdb

    # Open the ArcGIS Pro project
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
    time.sleep(10)

    # Restart the script in a new process so that any locks are released 
    subprocess.Popen([sys.executable, '-u'] + sys.argv + ["edit"], close_fds=True)

    # Exit the current script to ensure it stops completely
    sys.exit()


#######################
# modify  network
#######################

'''**Follow the instructions below for the appropriate section to make edits**


Project Type | Action 
---- | ----
New construction (line) | Add new line to network and make appropriate connections 
Widening (line) | Reduce travel time along links to free flow speed (Julie will ask Suzy what the travel time benefit is in the model) 
Operational (line) | Reduce travel time along links to average of free flow speed and peak hour speed 
Restripe (when is basically widening) (line) | Reduce travel time along links to free flow speed 
New interchange (point)  | Add connections in network 
Grade-separated crossing | Add new line across intersection (no intersection impedance) '''

def modify_network():

    # launch arcgis pro
    config = load_yaml('0_config.yaml')
    arcgis_pro = config['arcgis_pro']   
    print('--Opening arcgis pro...')
    print('--Remember to save the edits, leave the new/edited features selected, and save the project')
    try:
        subprocess.run([arcgis_pro, aprx_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to open ArcGIS Pro: {e}", "error")
        return
    

    #================================
    # resume after arcgis pro closes
    #================================

    print('--arcgis pro closed, resuming script')
    bpa = arcpy.management.MakeFeatureLayer(  os.path.join(target_gdb, r"NetworkDataset\BikePedAuto"),  "BPA")

    # Open the ArcGIS Pro project
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    map_name = "Map"
    m = aprx.listMaps(map_name)[0]
    bpa = m.listLayers(layer_name)[0]
    
    ## New construction (line)
    print(f'--recalculating attributes for {combo_value}')
    if combo_value == 'New Construction': 
        
        '''For new construction, new lines and connections are added to the BPA-Scenario (BikePedAuto) layer in the Network Dataset.'''

        # UPDATE LENGTHS FOR SELECTED FEATURES - SELECT ONLY AFFECTED FEATURES TO KEEP RUN TIME REASONABLE
        # this will likely throw some TypeErrors if the selectio includes non-roadway segments - ignore these!
        if int(arcpy.management.GetCount(bpa)[0]) < 250:
            arcpy.management.CalculateField(bpa, "Length_Miles", '!shape.length@miles!', "PYTHON3", None, "DOUBLE")
            arcpy.management.CalculateField(bpa, "DriveTime", '!Length_Miles! / (!Speed! / 60)', "PYTHON3", None, "DOUBLE")
            arcpy.management.CalculateField(bpa, "PedestrianTime", '!Length_Miles! / (3 / 60)', "PYTHON3", None, "DOUBLE")
            arcpy.management.CalculateField(bpa, "BikeTime", '!Length_Miles! / (11 / 60)', "PYTHON3", None, "DOUBLE")
        else:
            print("Error: operation will affect more than 250 features. Did you select only the intended target?")
    
    ## Widening / Restripe (line)
    elif combo_value == 'Widening | Restripe': 

        '''For capacity expansion projects or restriping projects that add a lane, the DriveTime attribute is reduced from the Peak Hour speed to the Free Flow speed (or by 15% when travel demand model travel times are not available).'''


        # UPDATE LENGTHS FOR SELECTED FEATURES - SELECT ONLY AFFECTED FEATURES TO KEEP RUN TIME REASONABLE
        # this will likely throw some TypeErrors if the selectio includes non-roadway segments - ignore these!
        if int(arcpy.management.GetCount(bpa)[0]) < 200:
            arcpy.management.CalculateField(
                bpa, "PK_SPD", '!FF_SPD!', "PYTHON3", None, "DOUBLE"
            )
            arcpy.management.CalculateField(
                bpa, "DriveTime_Peak", 
                '!Length_Miles! / (!FF_SPD! / 60)', "PYTHON3", None, "DOUBLE"
            )
            arcpy.management.CalculateField(
                bpa, "DriveTime", 
                '!DriveTime_Peak! if !DriveTime_Peak! else DriveTime * 0.85', 
                "PYTHON3", None, "DOUBLE"
            )
        else:
            print("Warning: operation will affect more than 200 features - did you select only the intended target?")

    ## Operational (line)
    elif combo_value == 'Operational': 
    
        '''Operational improvements are assumed to improve user operating speeds during the peak hour, but less so than a capacity expansion project. Reduce travel time along links to average of free flow speed and peak hour speed (or by 10% when travel demand model travel times are not available).'''

        # UPDATE LENGTHS FOR SELECTED FEATURES - SELECT ONLY AFFECTED FEATURES TO KEEP RUN TIME REASONABLE
        # this will likely throw some TypeErrors if the selectio includes non-roadway segments - ignore these!
        expression = '(!DriveTime_Peak! + !DriveTime_FF!) / 2 if !DriveTime_Peak! else !DriveTime! * 0.9'
        if int(arcpy.management.GetCount(bpa)[0]) < 100:
            arcpy.management.CalculateField(bpa, "DriveTime", expression, "PYTHON3", None, "DOUBLE")
        else:
            print("Warning: operation will affect more than 100 features - did you select only the intended target?")


    ## New interchange (point) 
    elif combo_value == 'New Interchange': 
        '''Add connections in network.'''
        pass



    ## Grade-separated crossing
    elif combo_value == 'Grade-separated Crossing': 
        '''Dissolve the segments of each road or path such that the segments no longer break at the intersection. Add additional connector features as needed, Then run the cell below to update the travel time values.'''

        # UPDATE LENGTHS FOR SELECTED FEATURES - SELECT ONLY AFFECTED FEATURES TO KEEP RUN TIME REASONABLE
        # this will likely throw some TypeErrors if the selectio includes non-roadway segments - ignore these!
        if int(arcpy.management.GetCount(bpa)[0]) < 100:
            arcpy.management.CalculateField(
                bpa, "Length_Miles", '!shape.length@miles!', 
                "PYTHON3", None, "DOUBLE"
            )
            arcpy.management.CalculateField(
                bpa, "DriveTime", '!Length_Miles! / (!Speed! / 60)', 
                "PYTHON3", None, "DOUBLE"
            )
            arcpy.management.CalculateField(
                bpa, "PedestrianTime", '!Length_Miles! / (3 / 60)', 
                "PYTHON3", None, "DOUBLE"
            )
            arcpy.management.CalculateField(
                bpa, "BikeTime", '!Length_Miles! / (11 / 60)', 
                "PYTHON3", None, "DOUBLE"
            )
        else:
            print("Warning: operation will affect more than 100 "
                "features - did you select only the intended target?")
    

    # clear the selection before creating the new network dataset
    try:
        arcpy.management.SelectLayerByAttribute(bpa, "CLEAR_SELECTION")
    except:
        pass

    # remove the bpa layer and close the project
    m.removeLayer(bpa)
    aprx.save()
    del aprx


    # build the newly created network dataset
    print('--building the modified network')
    nd = os.path.join(target_gdb, r"NetworkDataset\NetworkDataset_ND")
    arcpy.CheckOutExtension("Network")
    ato.build(nd)
    arcpy.CheckInExtension("Network")


###################
# MAIN
###################
def main():
    if "edit" in sys.argv:
        print('--begin editing')
        modify_network()
        print('--scripts finished')
    else:
        print('--begin scenario network prep')
        prepare_network()
    
if __name__ == "__main__":
    main()