import arcpy
import os
import errno
from arcgis.features import SpatialDataFrame
import pandas as pd
import math
import time

def survey_weight(t):
    if t <= 3:
        return 1
    elif (t > 3) & (t <= 20):
        return -0.0382 * t + 1.1293
    elif t > 20:
        return 1/(1 + math.exp(0.1092 * t - 1.5604))
    else:
        return 0

def score(gdb, mode, centroids = r"shp\taz_wfrc.gdb\taz_centroids_snapped",
          nd = r"NetworkDataset\NetworkDataset_ND", out_table = "scores", 
          test = False):
    """Given a network dataset, solve and score TAZ ATO
    
    Keyword arguments:
    gdb -- the path to the filegeodatabase containing the network dataset used for analysis
    nd -- the path of the network dataset within gdb. Default: "NetworkDataset\\NetworkDataset_ND"
    out_table -- name of the output table with ATO scores (written to gdb)
    mode -- evaluation mode ("Driving" | "Transit")
    test -- set to True to run on the sample TAZs only to improve processing time

    This function uses Network Analyst (arcpy.nax) to solve routes between all TAZs.
    all supplied TAZ centroids. A typical run takes about ten minutes for the full 
    2800 TAZ dataset or about 1 minute for the sample TAZ dataset.
    """
    start = time.time()

    arcpy.CheckOutExtension("network")

    base_path = os.path.abspath(".")

    # location of the file geodatabase with the WFRC TAZ shapes and TAZ centroids    
    arcpy.env.workspace = "ato.gdb"

    # if testing, use a subset of centroids
    if test:
        centroids = r"shp\taz_wfrc.gdb\taz_centroids_sample"

    nd_layer_name = "wfrc_mm"

    nd_path = os.path.join(gdb, nd)

    print("Solving skim using {0} network for {1} .".format(mode, nd_path))
    arcpy.AddMessage("Creating network from {}".format(nd_path))

    if arcpy.Exists(nd_path):
        arcpy.nax.MakeNetworkDatasetLayer(nd_path, nd_layer_name)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), nd_path)

    odcm = arcpy.nax.OriginDestinationCostMatrix(nd_layer_name)

    odcm.travelMode = mode

    # do not consider travel times beyond 60 minutes
    odcm.defaultImpedanceCutoff = 60 

    odcm.lineShapeType = arcpy.nax.LineShapeType.NoLine

    # Load inputs using field mappings, including the pre-calculated location fields
    field_mappings_origins = odcm.fieldMappings(arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, True)

    # Load origins, mapping the "CO_TAZID" field to the "Name" property of the Origins class
    field_mappings_origins["Name"].mappedFieldName = "CO_TAZID"
    odcm.load(
        arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, 
        centroids, 
        field_mappings_origins
    )

    # Load destinations, mapping the "CO_TAZID" field to the "Name" property of the Origins class 
    field_mappings_destinations = odcm.fieldMappings(arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, True)
    field_mappings_destinations["Name"].mappedFieldName = "CO_TAZID"
    odcm.load(
        arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, 
        centroids, 
        field_mappings_destinations
    )


    # Solve the OD skim matrix
    result = odcm.solve()

    # Export the results to a feature class
    if result.solveSucceeded:
        result.export(arcpy.nax.OriginDestinationCostMatrixOutputDataType.Lines, r"memory\output_lines")
    else:
        print("Solve failed")
        print(result.solverMessages(arcpy.nax.MessageSeverity.All))

    od = pd.DataFrame.spatial.from_featureclass(r"memory\output_lines")

    if od['Total_Time'].mean() < 1:
        print("Network validation: FAIL")
        print("Travel Times: ", od['Total_Time'].head())
        raise ValueError('Network Travel Times are Zero - Invalid Network')

    # Join the TAZ data
    od['DestinationName'] = od['DestinationName'].astype(int)

    # this will fail if the TAZ layer hasn't been prepared appropriately
    # refer to 1_network_setup.ipynb
    taz = pd.DataFrame.spatial.from_featureclass(centroids)

    taz.drop(columns=taz.columns.difference(['CO_TAZID', 'HH', 'JOB']), inplace=True)
    
    region_job_per_hh = taz['JOB'].sum() / taz['HH'].sum()
    print("Regional Jobs per HH Ratio: {}".format(region_job_per_hh))

    df = pd.merge(od, taz, left_on="DestinationName", right_on="CO_TAZID")

    df.rename(columns={"OriginName": "Origin_TAZID",
                       "DestinationName": "Destination_TAZID"},
              inplace=True)

    # Weight outputs
    df['survey_weight'] = df['Total_Time'].apply(lambda x: survey_weight(x)).round(3)

    df['accessible_jobs'] = round(df['survey_weight'] * df['JOB'])
    df['accessible_hh'] = round(df['survey_weight'] * df['HH'])

    # keep only relevant columns
    keep_cols = ['Origin_TAZID', 'Destination_TAZID', 'Total_Time', 'accessible_jobs', 'accessible_hh']
    df.drop(columns=df.columns.difference(keep_cols), inplace=True)

    # save table to input GDB
    df.spatial.to_table(os.path.join(gdb, out_table))

    df_summary = df.groupby('Origin_TAZID').agg(
        accessible_jobs=pd.NamedAgg(column='accessible_jobs', aggfunc=sum),
        accessible_hh=pd.NamedAgg(column='accessible_hh', aggfunc=sum)
    )
    df_summary['CO_TAZID'] = df_summary.index.astype(int)
    taz_ato = pd.merge(df_summary, taz, on="CO_TAZID")

    # Apply WFRC TAZ-based ATO formula
    taz_ato['ato'] = round((taz_ato['accessible_hh'] * taz_ato['JOB'] + taz_ato['accessible_jobs'] * taz_ato['HH'] * region_job_per_hh) / 
                      (taz_ato['HH'] * region_job_per_hh + taz_ato['JOB']))

    #taz_summary.to_csv(r'tmp\scores_summary.csv')
    taz_ato.spatial.to_table(os.path.join(gdb, out_table + "_summary"))

    # save table to input GDB
    print("Scores written to {}".format(os.path.join(gdb, out_table + "_summary")))

    print("Network ATO: {}".format(taz_ato['ato'].sum()))
    
    end = time.time()
    duration = (end-start)/60
    print("Skim Matrix Solve Time (mins): {}".format(duration))
    arcpy.AddMessage("Skim Matrix Solve Time: {}".format(duration))

    return