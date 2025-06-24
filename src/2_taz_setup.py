print('--begin TAZ setup')
import sys
import os
import arcpy
import shutil
import pandas as pd
import yaml
import logging
from ato_tools import ato

arcpy.env.overwriteOutput = True
arcpy.env.parallelProcessingFactor = "90%"

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
    
# set up logger
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    filename='logs/2_taz_setup.log',  # Log to a file (optional)
    filemode='a'  # Append to the file (use 'w' to overwrite)
)
logging.info("begin TAZ setup")
    
# source files and fields
config = load_yaml('src/0_config.yaml')
source_taz = config['source_taz']
hh_source_field = config['hh_source_field'] # field containing TAZ household count
job_source_field = config['job_source_field'] # field containing TAZ job count
tazid_source_field = config['tazid_source_field'] # unique identifier for the zones



crs = arcpy.SpatialReference(26912)

# Set the XYResolution environment to a linear unit
arcpy.env.XYResolution = "0.01 Meters"
arcpy.env.XYTolerance = "0.1 Meters"

base_path = os.path.abspath(".")
base_gdb = os.path.join(base_path, "baseline.gdb")

## TAZ Setup

'''Configure the TAZ table and centroid locations.'''

# Copy TAZ Polygons to Baseline - keeping only CO_TAZID Field
print('--coping taz geometry')
logging.info("coping taz geometry")
# arcpy.conversion.FeatureClassToFeatureClass( source_taz, base_gdb,  "taz",  '',  r'taz_id "taz_id" true true false 4 Long 0 0,First,#,shp\taz.gdb\ATO,CO_TAZID,-1,-1') # deprecated
taz_fc = os.path.join(base_gdb, "taz")
arcpy.conversion.ExportFeatures(source_taz, taz_fc, field_mapping=r'taz_id "taz_id" true true false 4 Long 0 0,First,#,shp\taz.gdb\ATO,CO_TAZID,-1,-1')


# calculate area
print('--recalculating area')
logging.info("recalculating area")
arcpy.management.CalculateGeometryAttributes(
    taz_fc, geometry_property=[["square_meters_taz", "AREA_GEODESIC"]],  area_unit="SQUARE_METERS"
)

# copy table of taz_id, hh, and job to baseline gdb
taz_table = pd.DataFrame.spatial.from_featureclass(source_taz)

# check if specified se fields in yaml are present
for f in [hh_source_field, job_source_field]:
    if f not in taz_table.columns:
        sys.exit(f"Error: Field {(f)} not present in TAZ SE table, please recheck the data")

taz_table['hh'] = taz_table[hh_source_field]
taz_table['job'] = taz_table[job_source_field]
taz_table['taz_id'] = taz_table[tazid_source_field]
taz_table.drop(columns=taz_table.columns.difference(['taz_id', 'hh', 'job']), inplace=True)
taz_table.spatial.to_table(os.path.join(base_gdb, "taz_table"))

# calculate TAZ centroids
# (the arcpy "Feature to Point" tool makes this easier but requires an advanced license)
logging.info("calculating xy coordinates")
arcpy.management.CalculateGeometryAttributes(os.path.join(base_gdb, "taz"), "x CENTROID_X;y CENTROID_Y",  '', '', crs, "SAME_AS_INPUT")
arcpy.management.XYTableToPoint(os.path.join(base_gdb, "taz"), os.path.join(base_gdb, "taz_centroids"), 'x', 'y', None, crs)
taz_centroids = arcpy.management.MakeFeatureLayer(os.path.join(base_gdb, "taz_centroids"), "taz_centroids")
arcpy.management.DeleteField(os.path.join(base_gdb, "taz"), ['x','y'])

'''Note, snapping TAZ centroids to the network can introduce some unintended variation in ATO between TAZs if the centroid snaps to a location only accessible via a circuitous route, to a roadway outside of the TAZ boundaries, etc. Also note, centroids are snapped to auto network. Additional snapping happens within the network solver configuration for transit and bicycle routes. None of this should materially affect the estimated change in ATO for a given project.'''

# snap taz centroids to network
# reqires ArcGIS Standard or Advanced
# this step can be skipped but is recommended
print('--snapping BPA layer')
logging.info("snapping BPA layer")
bpa_snap = arcpy.management.MakeFeatureLayer(os.path.join(base_gdb, r"NetworkDataset\BikePedAuto"),  "bpa_snap")
arcpy.management.SelectLayerByAttribute(bpa_snap, "NEW_SELECTION", "AutoNetwork = 'Y' And VERT_LEVEL = '0' And CartoCode NOT IN ('1 Interstates')")
arcpy.edit.Snap(taz_centroids,  [[bpa_snap, 'END','10000 Feet']])

# Finally, create a testing layer with 25 randomly selected centroids
import random
arcpy.management.SelectLayerByAttribute(taz_centroids, "CLEAR_SELECTION")

feature_count = int(arcpy.management.GetCount(taz_centroids).getOutput(0))
rnd_set = set([]) 
while len(rnd_set) < 25: 
    rnd_set.add(random.randint(0, feature_count-1))
where = 'OBJECTID in ({0})'.format(','.join(map(str,rnd_set)))
arcpy.management.SelectLayerByAttribute(taz_centroids, "NEW_SELECTION", where)
taz_centroids_sample = arcpy.conversion.FeatureClassToFeatureClass('taz_centroids', base_gdb, "taz_centroids_sample")
arcpy.management.SelectLayerByAttribute('taz_centroids', "CLEAR_SELECTION")

## Baseline Scoring

'''
Calculate ATO for our baseline modal networks.

Finally, we create a copy of the baseline network dataset to use as a template for scenario networks.

Note, typical solve times:

* Driving: 20 minutes
* Transit: 4 - 5 minutes
* Cycling: 4 - 5 minutes

If solve times deviate signficantly or if the cell below produces a ValueError, rebuild the network dataset using `ato.build(os.path.join(base_gdb, r'NetworkDataset//NetworkDataset_ND'))` and re-solving. (This is related to the Network Analyst attribute mismatch issue.)
'''
print('--calculating baseline skims (~20 minutes)')
logging.info("calculating baseline skims")
for mode in ['Driving', 'Transit', 'Cycling']:
    ato.skim(
        nd = os.path.join(base_gdb, r'NetworkDataset\NetworkDataset_ND'),
        mode = mode,
        centroids = os.path.join(base_gdb, 'taz_centroids'),
        out_table = os.path.join(base_gdb, 'skim_' + mode.lower())
    )
logging.info("baseline skims complete")

print('--calculating baseline scores')
logging.info("calculating baseline scores")
for mode in ['driving', 'transit', 'cycling']:
    ato.score(
        mode = mode,
        skim_matrix = os.path.join(base_gdb, 'skim_' + mode),
        taz_table = os.path.join(base_gdb, 'taz_table'),
        out_table = os.path.join(base_gdb, 'ato_' + mode)
    )
logging.info("baseline scores calculated")

# Create "template" to use for mods
# Note: if this fails, try starting ArcGIS Pro.
print('--creating template geodatabase for mods')
logging.info("creating template geodatabase for mods")
if os.path.isdir(r"scenario\scenario_template.gdb"):
    shutil.rmtree(r"scenario\scenario_template.gdb")

arcpy.management.CreateFileGDB("scenario", "scenario_template")

# Copy our baseline network dataset to our dataset for modification
arcpy.management.Copy(r"baseline.gdb\NetworkDataset", r"scenario\scenario_template.gdb\NetworkDataset")
arcpy.management.Copy(r"baseline.gdb\taz_table", r"scenario\scenario_template.gdb\taz_table")

# delete existing network
arcpy.management.Delete(r"scenario\scenario_template.gdb\NetworkDataset\NetworkDataset_ND")

# if open in ArcGIS Pro, remove all layers
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    mp = aprx.listMaps("Map")[0]
    for rmlyr in mp.listLayers():    
        if rmlyr.name not in ['World Topographic Map', 'World Hillshade']:        
            mp.removeLayer(rmlyr)
except OSError:
    pass
print('--TAZ setup complete!')
logging.info("TAZ setup complete")