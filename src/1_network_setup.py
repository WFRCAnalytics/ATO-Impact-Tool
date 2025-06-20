print('--begin network setup')
import sys
import os
import arcpy
import shutil
import yaml
import logging
from ato_tools import ato


def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    
# set up logger
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    filename='logs/1_network_setup.log',  # Log to a file (optional)
    filemode='a'  # Append to the file (use 'w' to overwrite)
)
logging.info("begin network setup")


# source files and fields
config = load_yaml('src/0_config.yaml')
source_network_dataset = config['source_network_dataset']
source_tdm = config['source_tdm']

# src = os.path.join(os.path.abspath("."), 'src')
# if src not in sys.path:
#     sys.path.append(src)


# Set the XYResolution environment to a linear unit
arcpy.env.XYResolution = "0.01 Meters"
arcpy.env.XYTolerance = "0.1 Meters"

# UTM 12N
crs = arcpy.SpatialReference(26912)
base_path = os.path.abspath(".")

base_gdb = os.path.join(base_path, "baseline.gdb")

arcpy.CheckOutExtension("network")
logging.info("network extension check out")

# Baseline Network Dataset Setup

'''
The cells below:
2. Copy the Multimodal network dataset and delete the layers that will be replaced with clipped versions
3. Clip the NetworkDataset>BikePedAuto and NetworkDataset>Network_Dataset_ND_Junctions layers using 5 mile buffer around the Wasatch Front TAZ layer
4. Create and fill RoadClass attribute to a usable hierarchy value
5. Join the TDM data for speeds

** Note: This notebook can be run either within or outside of ArcGIS Pro. It is recommended to run this notebook outside of ArcGIS Pro. If running within Pro, sometimes sequential execution of the cells below will produce a "Cannot acquire a lock" error. If this happens, just re-run the cell. Esri weirdness! **

### Network Setup Notes

Vertical Elevation - the current dataset does not contain the necessary attributes to establish vertical connectivity. Elevation is not used.

Hierarchy - oddly, adding a heirarchy for routing seems to worsen performance. Hierarchy is not used.

'''

# if baseline GDB exists, delete it
if os.path.isdir(base_gdb):
    print('--deleting existing base gdb')
    shutil.rmtree(base_gdb)

arcpy.management.CreateFileGDB(base_path, "baseline")

# Copy NetworkDataset to our working GDB - 50 seconds
print('--copying gdb (50 seconds)')
logging.info("copying gdb")
arcpy.management.Copy(source_network_dataset,  os.path.join(base_gdb, "NetworkDataset"))

# delete existing network
print('--deleting network dataset')
arcpy.management.Delete(os.path.join(base_gdb, r"NetworkDataset\NetworkDataset_ND"))

# create a feature layer from bikepedauto
bpa = arcpy.management.MakeFeatureLayer(os.path.join(base_gdb, r"NetworkDataset\BikePedAuto"),   "BPA")

# add hierarchy to clipped BikePedAuto
arcpy.management.AddField(bpa, "hierarchy", "SHORT")

# if this fails due to a "lock" error try running again
# note, this field was previously RoadClass and is now CartoCode
expression = "getClass(!CartoCode!)"

codeblock = """
hierarchy = {
	'1 Interstates': 1,
	'2 US Highways, Separated': 1,
	'3 - Paved Shared Use': 3,
	'3 US Highways, Unseparated': 1,
	'4 Major State Highways, Separated': 1,
	'5 Major State Highways, Unseparated': 1,
	'6 Other State Highways (Institutional)': 1,
	'7 Ramps, Collectors': 2,
	'8 - Bridge, Tunnel': 2,
	'8 Major Local Roads, Paved': 2,
	'9 - Link': 3,
	'9 Major Local Roads, Not Paved': 3,
	'10 Other Federal Aid Eligible Local Roads': 2,
	'11 Other Local, Neighborhood, Rural Roads': 3,
	'12 Other': 3,
	'13 Non-road feature': None,
	'14 Driveway': None,
	'15 Proposed': None,
     '16 4WD and/or high clearance may be required': None,
	'17 Service Access Roads': None,
	'99 - UDOT FAE Calibration (Non-Road Feature)': None
}
def getClass(rc):
    return 3 if rc is None else hierarchy[rc]
"""

# Execute CalculateField 
arcpy.management.CalculateField(bpa, "hierarchy", expression, "PYTHON3", codeblock)

# Select non-road features
arcpy.management.SelectLayerByAttribute(bpa, "NEW_SELECTION", "hierarchy IS NULL")

print('--deleting non road bpa features (50 seconds)')
logging.info("deleting non road bpa features ")
arcpy.management.DeleteFeatures(bpa) # 50 seconds
# sometimes this fails - removing from map and adding again seems to help

### Join in Speed Data
'''WFRC has provided free flow and peak hour speed data from their TDM. We will join this to the network dataset for later use when roughly estimating the short-term improvement in automobile mobility associated with roadway widening.'''

tdm = arcpy.conversion.FeatureClassToFeatureClass(source_tdm,base_gdb, "TDM")

# Create and calculate PK_SPD field based on minimum (peak time) speed
arcpy.management.CalculateField(tdm, "PK_SPD",  "min(!AM_SPD!,!MD_SPD!,!PM_SPD!,!EV_SPD!)",  "PYTHON3", '', "DOUBLE")

# Spatially join TDM travel times to MM network:
field_spec = """Name "Name" true true false 50 Text 0 0,First,#,BikePedAuto,Name,0,50;
Oneway "Oneway" true true false 2 Text 0 0,First,#,BikePedAuto,Oneway,0,2;
Speed "Speed" true true false 2 Short 0 0,First,#,BikePedAuto,Speed,-1,-1;
AutoNetwork "AutoNetork" true true false 1 Text 0 0,First,#,BikePedAuto,AutoNetwork,0,1;
BikeNetwork "BikeNetwork" true true false 1 Text 0 0,First,#,BikePedAuto,BikeNetwork,0,1;
PedNetwork "PedNetwork" true true false 1 Text 0 0,First,#,BikePedAuto,PedNetwork,0,1;
SourceData "SourceData" true true false 15 Text 0 0,First,#,BikePedAuto,SourceData,0,15;
DriveTime "DriveTime" true true false 8 Double 0 0,First,#,BikePedAuto,DriveTime,-1,-1;
BikeTime "BikeTime" true true false 8 Double 0 0,First,#,BikePedAuto,BikeTime,-1,-1;
PedestrianTime "PedestrianTime" true true false 8 Double 0 0,First,#,BikePedAuto,PedestrianTime,-1,-1;
Length_Miles "Length_Miles" true true false 8 Double 0 0,First,#,BikePedAuto,Length_Miles,-1,-1;
ConnectorNetwork "ConnectorNetwork" true true false 1 Text 0 0,First,#,BikePedAuto,ConnectorNetwork,0,1;
CartoCode "CartoCode" true true false 50 Text 0 0,First,#,BikePedAuto,CartoCode,0,50;
AADT "AADT" true true false 4 Long 0 0,First,#,BikePedAuto,AADT,-1,-1;
AADT_YR "AADT_YR" true true false 4 Text 0 0,First,#,BikePedAuto,AADT_YR,0,4;
BIKE_L "BIKE_L" true true false 4 Text 0 0,First,#,BikePedAuto,BIKE_L,0,4;
BIKE_R "BIKE_R" true true false 4 Text 0 0,First,#,BikePedAuto,BIKE_R,0,4;
VERT_LEVEL "VERT_LEVEL" true true false 25 Text 0 0,First,#,BikePedAuto,VERT_LEVEL,0,25;
hierarchy "hierarchy" true true false 2 Short 0 0,First,#,BikePedAuto,hierarchy,-1,-1;
FF_SPD "FF_SPD" true true false 8 Double 0 0,First,#,TDM,FF_SPD,-1,-1;
PK_SPD "PK_SPD" true true false 8 Double 0 0,First,#,TDM,PK_SPD,-1,-1;
LANES "LANES" true true false 8 Double 0 0,First,#,TDM,LANES,-1,-1"""

tdm_sj = arcpy.analysis.SpatialJoin(
    bpa, 
    tdm, 
    os.path.join(base_gdb, "TDM_SpatialJoin"), 
    "JOIN_ONE_TO_ONE", 
    "KEEP_ALL", 
    field_spec, 
    "HAVE_THEIR_CENTER_IN", # "SHARE_A_LINE_SEGMENT_WITH"
)

# copy attributes back to the BikePedAuto
arcpy.management.JoinField(
    bpa, 
    "OBJECTID", 
    tdm_sj, 
    "TARGET_FID", 
    "LANES;FF_SPD;PK_SPD"
)

# Calculate drive times based on peak hour TDM speeds
codeblock = """
def getSpeed(spd, len):
    return None if spd is None else float(60*len/spd)
"""
print('--calculating drive times')
logging.info("calculating drive times")
arcpy.management.CalculateField(bpa, "DriveTime_Peak",  "getSpeed(!PK_SPD!, !Length_Miles!)",  "PYTHON3", codeblock, "DOUBLE")
arcpy.management.CalculateField(bpa, "DriveTime_FF",    "getSpeed(!FF_SPD!, !Length_Miles!)",  "PYTHON3", codeblock, "DOUBLE")

# Update Drive Time based on TDM peak value when set/exists
arcpy.management.CalculateField( bpa,  "DriveTime",   "!DriveTime! if !DriveTime_Peak! == None else !DriveTime_Peak!", "PYTHON3", None, "DOUBLE")

# clean up temporary layers'=
print('--cleanup')
logging.info("Cleaning up temporary layers")
arcpy.management.Delete(r"memory\taz_buffer")
arcpy.management.Delete(os.path.join(base_gdb, "TDM_SpatialJoin"))
arcpy.management.Delete(os.path.join(base_gdb, "TDM"))

# finally, build the network dataset - 60 seconds
print('--rebuilding the network dataset (60 seconds)')
logging.info("rebuilding the network dataset")
ato.build(os.path.join(base_gdb, r'NetworkDataset\NetworkDataset_ND'))
logging.info("network dataset rebuild complete")
arcpy.CheckInExtension("network")
print('--network setup complete!')
logging.info("network setup complete")













