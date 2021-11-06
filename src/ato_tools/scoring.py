import arcpy
import os
import errno
from arcgis.features import SpatialDataFrame
import pandas as pd
import math

arcpy.CheckOutExtension("network")

def survey_weight(t):
    if t <= 3:
        return 1
    elif (t > 3) & (t <= 20):
        return -0.0382 * t + 1.1293
    elif t > 20:
        return 1/(1 + math.exp(0.1092 * t - 1.5604))
    else:
        return 0

def score(nd_gdb, nd = r"NetworkDataset\NetworkDataset_ND", out_table = "scores", mode = "Driving", test = False):
    """Given a network dataset, solve and score TAZ ATO
    
    Keyword arguments:
    nd_gdb -- the path to the network dataset used for analysis


    This function uses Network Analyst (arcpy.nax) to solve routes between
    all supplied TAZ centroids.
    """

    base_path = os.path.abspath(".")

    arcpy.env.workspace = os.path.join(base_path, "ato.gdb")

    # location of the file geodatabase with the WFRC TAZ shapes and TAZ centroids    
    ato_gdb = os.path.join(base_path, r"shp\taz_wfrc.gdb")

    if test:
        centroids = os.path.join(ato_gdb, "taz_centroids_sample")
    else:
        centroids = os.path.join(ato_gdb, "taz_centroids_snapped")

    nd_layer_name = "wfrc_mm"

    nd_path = os.path.join(nd_gdb, nd)

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
    odcm.load(arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, centroids, field_mappings_origins)

    # Load destinations, mapping the "CO_TAZID" field to the "Name" property of the Origins class 
    field_mappings_destinations = odcm.fieldMappings(arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, True)
    field_mappings_destinations["Name"].mappedFieldName = "CO_TAZID"
    odcm.load(arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, centroids, field_mappings_destinations)


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

    taz = pd.DataFrame.spatial.from_featureclass(os.path.join(ato_gdb, "ATO"))

    taz = taz[['CO_TAZID', 'HH_19', 'JOB_19']] #, 'JOBAUTO_19', 'HHAUTO_19', 'JOBTRANSIT_19', 'HHTRANSIT_19']]

    # rename TAZ fields to make this easier to accomodate updates in future years
    taz.rename(columns={'HH_19': 'HH', 'JOB_19': 'JOB'}, inplace=True)

    od['DestinationName'] = od['DestinationName'].astype(int)

    df = pd.merge(od, taz, left_on="DestinationName", right_on="CO_TAZID", )

    df.rename(columns={"OriginName": "Origin_TAZID",
                       "DestinationName": "Destination_TAZID"},
              inplace=True)

    # Weight outputs
    df['survey_weight'] = df['Total_Time'].apply(lambda x: survey_weight(x)).round(3)

    df['weighted_jobs'] = round(df['survey_weight'] * df['JOB'])
    df['weighted_hh'] = round(df['survey_weight'] * df['HH'])

    region_job_per_hh = df['JOB'].sum() / df['HH'].sum()

    #df['ato'] = df['weighted_jobs'] + df['weighted_hh']

    # Apply WFRC TAZ-based ATO formula
    df['ato'] = round((df['weighted_hh'] * df['JOB'] + df['weighted_jobs'] * df['HH'] * region_job_per_hh) / 
                      (df['HH'] * region_job_per_hh + df['JOB']))

    df.head()
    # write to disk
    df = df[['Origin_TAZID', 'Destination_TAZID', 'Total_Time',
             'weighted_jobs', 'weighted_hh', 'ato']] # .to_csv(r'tmp\scores.csv')
    
    df.spatial.to_table(os.path.join(nd_gdb, out_table))

    # save table to input GDB
    #arcpy.conversion.TableToTable(r'tmp\scores.csv', nd_gdb, out_name)

    taz_summary = df.groupby('Origin_TAZID').agg(
        jobs=pd.NamedAgg(column='weighted_jobs', aggfunc=sum),
        hh=pd.NamedAgg(column='weighted_hh', aggfunc=sum),
        ato=pd.NamedAgg(column='ato', aggfunc=sum)
    )

    #taz_summary.to_csv(r'tmp\scores_summary.csv')
    taz_summary.spatial.to_table(os.path.join(nd_gdb, out_table + "_summary"))

    # save table to input GDB
    #arcpy.conversion.TableToTable(r'tmp\scores_summary.csv', nd_gdb, "scores_summary")

    print("Scores written to {}".format(os.path.join(nd_gdb, out_table + "_summary")))

    print("Network ATO: {}".format(taz_summary['ato'].sum()))
    
    return