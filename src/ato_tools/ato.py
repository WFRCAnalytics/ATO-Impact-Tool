import arcpy
import os
import pandas as pd
import time
import errno
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import math

test_centroids = os.path.join(os.path.abspath("."), r"baseline.gdb\taz_centroids_sample")

def _ato(jobs, accessible_jobs, hh, accessible_hh, job_per_hh):
    """WFRC's ATO weighting formula"""
    ato = 0
    if jobs + hh >= 1:
        ato = (
            (accessible_hh * jobs + 
             accessible_jobs * hh * job_per_hh) / 
            (jobs + hh * job_per_hh)
        )
    return ato


def _survey_weight(t):
    """WFRC's Distance Decay Function"""
    if t <= 3:
        return 1
    elif (t > 3) & (t <= 20):
        return -0.0382 * t + 1.1293
    elif t > 20:
        return 1/(1 + math.exp(0.1092 * t - 1.5604))
    else:
        return 0


def build(nd, template = None, validate = True):
    """Builds network dataset and runs diagnostics

    Keyword arguments:
    nd -- full path to network dataset to be built
    template -- optionally specify a network template xml file
    validate -- run post-build validation testing?
    """
    if arcpy.Exists(nd):
        arcpy.management.Delete(nd)

    # if no template specified, use project default
    if template == None:
        template = os.path.join(os.path.abspath("."), "network_template.xml")

    target_gdb = nd[:-len(r'\NetworkDataset\NetworkDataset_ND')]
    print(f"Target GDB: {target_gdb}")
    
    # create network dataset from template
    arcpy.nax.CreateNetworkDatasetFromTemplate(
        template,                 
        os.path.join(target_gdb, "NetworkDataset")
    )

    start = time.time()

    arcpy.nax.BuildNetwork(nd)

    end = time.time()

    duration = end-start
    print(f"Network Build Time (seconds): {duration}")
    if duration < 10:
        print("Warning: abnormally short build duration. Verify network validity.")
    
    if validate == True:
        test(nd)


def test(nd, mode = ['Cycling', 'Driving', 'Transit']):
    """ Test validity of network dataset by routing two points in SLC

    Keyword arguments:
    nd -- full path to network dataset to be tested
    mode -- a string or list of ['Cycling', 'Driving', 'Transit']

    Validate network dataset by solving a simple route between 
    two static points downtown and ensure travel times are > 1 
    minute and < 60 minutes for all modes (Refer to Esri Case #02899742)
    """
    arcpy.env.addOutputsToMap = False

    nd_layer_name = "Routing_ND"
    input_stops = r'shp\test_points\test_points.shp'
    output_routes = r'memory\routes'

    if isinstance(mode, str):
        mode = [mode]

    # Create a network dataset layer and get the desired travel mode for analysis
    arcpy.nax.MakeNetworkDatasetLayer(nd, nd_layer_name)

    for test_mode in mode:
        # Instantiate a Route solver object
        route = arcpy.nax.Route(nd_layer_name)

        # Set properties
        route.timeUnits = arcpy.nax.TimeUnits.Minutes
        route.routeShapeType = arcpy.nax.RouteShapeType.TrueShapeWithMeasures
        route.travelMode = test_mode
        
        # Load inputs and solve the analysis
        route.load(arcpy.nax.RouteInputDataType.Stops, input_stops)
        result = route.solve()

        # Export the results to a feature class
        if result.solveSucceeded:
            result.export(arcpy.nax.RouteOutputDataType.Routes, output_routes)
        else:
            print("Solved failed")
            print(result.solverMessages(arcpy.nax.MessageSeverity.All))

        # test if travel time between 1 and 60 minutes
        result = pd.DataFrame.spatial.from_featureclass(output_routes)
        travel_time = result.at[0,'Total_Minutes']
        if travel_time < 1 or travel_time > 60:
            msg = f"Invalid travel time {travel_time} for {mode}. See README"
            print(msg)
            raise Exception(msg)
        else:
            print(f"Network test passes for {test_mode}.")
            
    arcpy.env.addOutputsToMap = True


def skim(nd, mode = 'Driving', centroids = None, out_table = 'skim_matrix'):
    """Given a network dataset and set of points, solve a skim matrix of travel times between points
    
    Keyword arguments:
    nd -- full path of the network dataset to be used for scoring
    mode -- travel mode ("Driving" | "Transit" | "Cycling")
    centroids -- full path of feature class of centroids with taz_id, HH, and JOB fields
    out_table -- full path of output skim matrix

    This function uses Network Analyst (arcpy.nax) to solve routes between all TAZs.
    all supplied TAZ centroids. A typical run takes about ten minutes for the full 
    2800 TAZ dataset or about 1 minute for the sample TAZ dataset.
    """
    start = time.time()

    arcpy.CheckOutExtension("network")

    # avoid cluttering up the Contents pane with temporary layers
    arcpy.env.addOutputsToMap = False

    # location of the file geodatabase with the WFRC TAZ shapes and TAZ centroids    
    tmp_env = arcpy.env.workspace

    target_gdb = nd[:-len(r'\NetworkDataset\NetworkDataset_ND')]

    arcpy.env.workspace = target_gdb

    if centroids == None:
        centroids = os.path.join(target_gdb, r'taz_centroids')

    nd_layer_name = "wfrc_mm_nd"

    print(f"Solving skim using {mode} network for {nd} .")
    arcpy.AddMessage(f"Creating network from {nd}")

    if arcpy.Exists(nd):
        arcpy.nax.MakeNetworkDatasetLayer(nd, nd_layer_name)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), nd)

    odcm = arcpy.nax.OriginDestinationCostMatrix(nd_layer_name)

    odcm.travelMode = mode

    # do not consider travel times beyond 60 minutes
    odcm.defaultImpedanceCutoff = 60 

    odcm.lineShapeType = arcpy.nax.LineShapeType.NoLine

    # Load inputs using field mappings, including the pre-calculated location fields
    field_mappings_origins = odcm.fieldMappings(arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, True)

    # Load origins, mapping the "taz_id" field to the "Name" property of the Origins class
    field_mappings_origins["Name"].mappedFieldName = "taz_id"
    odcm.load(
        arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, 
        centroids, 
        field_mappings_origins
    )

    # Load destinations, mapping the "taz_id" field to the "Name" property of the Origins class 
    field_mappings_destinations = odcm.fieldMappings(arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, True)
    field_mappings_destinations["Name"].mappedFieldName = "taz_id"
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
        print("Travel Times: ", od['total_time'].head())
        raise ValueError('Network Travel Times are Zero - Invalid Network')

    # save table to input GDB
    od.spatial.to_table(out_table)

    # save table to input GDB
    print("Skim matrix written to " + out_table)

    end = time.time()
    duration = round((end-start)/60, 2)

    print(f"Skim Matrix Solve Time (mins): {duration}")
    arcpy.AddMessage(f"Skim Matrix Solve Time: {duration}")
    if duration < 2:
        print(f"Error with {nd}. Run ato.build('{nd}')")
        raise Exception('Skim matrix solve time too short. Consider rebuilding network.')


    arcpy.env.addOutputsToMap = True
    arcpy.env.workspace = tmp_env

    return True


def score(skim_matrix, taz_table, out_table, job_per_hh = None):
    """Given a skim matrix, solve and score TAZ ATO
    
    Keyword arguments:
    skim_matrix -- full path to skim matrix of travel times for scoring
    taz_table -- full path of table with taz_id, HH, and JOB fields
    out_table -- full path of output table with ATO scores
    job_per_hh -- override regional ratio of jobs per household for ATO weighting
    """
    start = time.time()

    arr = arcpy.da.TableToNumPyArray(skim_matrix, '*')
    od = pd.DataFrame(arr)

    if od['total_time'].mean() < 1:
        print("Network validation: FAIL")
        print("Travel Times: ", od['total_time'].head())
        raise ValueError('Network Travel Times are Zero - Invalid Network')

    # Join the TAZ data
    od['destination_name'] = od['destination_name'].astype(int)

    # this will fail if the TAZ layer hasn't been prepared appropriately
    # refer to 2_taz_setup.ipynb
    arr = arcpy.da.TableToNumPyArray(taz_table, ['taz_id', 'hh', 'job'])
    taz = pd.DataFrame(arr, columns=['taz_id', 'hh', 'job'])

    if job_per_hh == None:
        job_per_hh = round(taz['job'].sum() / taz['hh'].sum(), 5)
        print(f"Regional Jobs per HH Ratio: {job_per_hh}")

    df = pd.merge(od, taz, left_on="destination_name", right_on="taz_id")

    df.rename(columns={"origin_name": "origin_taz_id",
                       "destination_name": "destination_taz_id"},
              inplace=True)

    # Weight outputs
    df['survey_weight'] = df['total_time'].apply(lambda x: _survey_weight(x)).round(3)

    df['accessible_jobs'] = round(df['survey_weight'] * df['job'])
    df['accessible_hh'] = round(df['survey_weight'] * df['hh'])

    # keep only relevant columns
    keep_cols = ['origin_taz_id', 'destination_taz_id', 'total_time', 
                 'accessible_jobs', 'accessible_hh']
    df.drop(columns=df.columns.difference(keep_cols), inplace=True)

    # save table to input GDB
    # df.spatial.to_table(out_table + '_full') # not needed

    df_summary = df.groupby('origin_taz_id').agg(
        accessible_jobs=pd.NamedAgg(column='accessible_jobs', aggfunc=sum),
        accessible_hh=pd.NamedAgg(column='accessible_hh', aggfunc=sum)
    )
    df_summary['taz_id'] = df_summary.index.astype(int)
    taz_ato = pd.merge(df_summary, taz, on="taz_id")

    taz_ato['ato'] = taz_ato.apply(
        lambda x: _ato(
            x['job'],
            x['accessible_jobs'],
            x['hh'],
            x['accessible_hh'],
            job_per_hh
        ),
        axis=1
    ).round()

    #taz_summary.to_csv(r'tmp\scores_summary.csv')
    taz_ato.spatial.to_table(out_table)

    # save table to input GDB
    print(f"Scores written to {out_table}")

    ato_score = taz_ato['ato'].sum()
    print(f"Network ATO: {ato_score}")
    
    return ato_score


def diff(baseline, scenario, out_table = None):
    """Calculate and return difference between two ATO score tables.
    
    Keyword arguments:
    baseline -- full path to baseline ato score table output from score() function
    scenario -- full path to scenario ato score table output from score() function
    out_table -- Optional. Full path to write output table
    """

    field_list = ['taz_id', 'accessible_jobs', 'accessible_hh', 'ato']

    arr = arcpy.da.TableToNumPyArray(baseline, field_list)
    baseline = pd.DataFrame(arr, columns = field_list)

    arr = arcpy.da.TableToNumPyArray(scenario, field_list)
    scenario = pd.DataFrame(arr, columns = field_list)

    df = pd.merge(
        baseline, 
        scenario, 
        on='taz_id', 
        how="inner",
        suffixes=("_before", "_after")
    )

    df['diff_hh'] = df['accessible_hh_after'] - df['accessible_hh_before']
    df['diff_jobs'] = df['accessible_jobs_after'] - df['accessible_jobs_before']
    df['diff_ato'] = df['ato_after'] - df['ato_before']

    if out_table != None:
        df[['taz_id', 'diff_jobs', 'diff_hh', 'diff_ato']].spatial.to_table(out_table)

    score = df['diff_ato'].sum()

    print(f'Scenario score: {score}')

    return score
