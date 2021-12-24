import arcpy
import os
import pandas as pd
import time
import errno
from arcgis.features import SpatialDataFrame
import math


test_centroids = os.path.join(os.path.abspath("."), r"baseline.gdb\taz_centroids_sample")

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
    print("Target GDB: {}".format(target_gdb))
    
    # create network dataset from template
    arcpy.nax.CreateNetworkDatasetFromTemplate(
        template,                 
        os.path.join(target_gdb, "NetworkDataset")
    )

    start = time.time()

    arcpy.nax.BuildNetwork(nd)

    end = time.time()

    duration = end-start
    print("Network Build Time (seconds): {}".format(duration))
    if duration < 10:
        print("Warning: abnormally short build duration. Verify network validity.")
    
    if validate == True:
        test(nd)

def test(nd, mode = ['Cycling', 'Driving', 'Transit']):
    """ Test validity of network dataset by routing two points in SLC

    Keyword arguments:
    nd -- full path to network dataset to be tested
    mode -- a string or list of ['Cycling', 'Driving', 'Transit']
    Solve a simple route between two static points downtown and ensure
    travel times are > 1 minute and < 60 minutes for all modes
    Refer to Esri Case #02899742
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
            msg = "Invalid travel time {0} for {1}. See README".format(travel_time, mode)
            print(msg)
            raise Exception(msg)
        else:
            print("Network test passes for {}.".format(test_mode))
            
    arcpy.env.addOutputsToMap = True


def _survey_weight(t):
    if t <= 3:
        return 1
    elif (t > 3) & (t <= 20):
        return -0.0382 * t + 1.1293
    elif t > 20:
        return 1/(1 + math.exp(0.1092 * t - 1.5604))
    else:
        return 0

def skim(gdb, mode = 'Driving', nd = None, centroids = None, out_table = 'skim_matrix'):
    """Given a network dataset and set of points, solve a skim matrix of travel times between points
    
    Keyword arguments:
    nd -- input network datasetthe full path of the network dataset  to be used for scoring
    mode -- travel mode ("Driving" | "Transit" | "Cycling")
    centroids -- full path of feature class of centroids with CO_TAZID, HH, and JOB fields
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

    arcpy.env.workspace = gdb

    if nd == None:
        nd = os.path.join(gdb, r'NetworkDataset\NetworkDataset_ND')

    if centroids == None:
        centroids = os.path.join(gdb, r'taz_centroids')

    nd_layer_name = "wfrc_mm_nd"

    print("Solving skim using {0} network for {1} .".format(mode, nd))
    arcpy.AddMessage("Creating network from {}".format(nd))

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

    # save table to input GDB
    od.spatial.to_table(out_table)

    # save table to input GDB
    print("Skim matrix written to " + out_table)

    end = time.time()
    duration = round((end-start)/60, 2)

    print("Skim Matrix Solve Time (mins): {}".format(duration))
    arcpy.AddMessage("Skim Matrix Solve Time: {}".format(duration))
    if duration < 2.5:
        print("Error with {}. Run ato.build('{0}')".format(nd))
        raise Exception('Skim matrix solve time too short. Consider rebuilding network.')


    arcpy.env.addOutputsToMap = True
    arcpy.env.workspace = tmp_env

    return True


def _ato(jobs, accessible_jobs, hh, accessible_hh, job_per_hh):
    """Implment WFRC's ATO weighting formula"""
    if jobs + hh == 0:
        return 0
    else:
        ato = (
            (accessible_hh * jobs + 
             accessible_jobs * hh * job_per_hh) / 
            (jobs + hh * job_per_hh)
        )
        return ato


def score(gdb, skim_matrix = None, taz_table = None, job_per_hh = None, out_table = None):
    """Given a skim matrix, solve and score TAZ ATO
    
    Keyword arguments:
    gdb -- file gdb for taz_table and out_table if not specified
    skim_matrix -- skim matrix of travel times for scoring
    taz_table -- full path of table with CO_TAZID, HH, and JOB fields
    job_per_hh -- regional retio of jobs per household for ATO weighting
    out_table -- full path of output table with ATO scores

    This function ...
    """
    start = time.time()

    if taz_table == None:
        taz_table = os.path.join(gdb, r'taz_table')

    if out_table == None:
        out_table = os.path.join(gdb, r'ato')

    if skim_matrix == None:
        skim_matrix = os.path.join(gdb, 'skim_matrix')

    arr = arcpy.da.TableToNumPyArray(skim_matrix, '*')
    od = pd.DataFrame(arr)

    if od['Total_Time'].mean() < 1:
        print("Network validation: FAIL")
        print("Travel Times: ", od['Total_Time'].head())
        raise ValueError('Network Travel Times are Zero - Invalid Network')

    # Join the TAZ data
    od['DestinationName'] = od['DestinationName'].astype(int)

    # this will fail if the TAZ layer hasn't been prepared appropriately
    # refer to 2_taz_setup.ipynb
    arr = arcpy.da.TableToNumPyArray(taz_table, ['CO_TAZID', 'HH', 'JOB'])
    taz = pd.DataFrame(arr, columns=['CO_TAZID', 'HH', 'JOB'])

    if job_per_hh == None:
        job_per_hh = taz['JOB'].sum() / taz['HH'].sum()
        print("Regional Jobs per HH Ratio: {}".format(job_per_hh))

    df = pd.merge(od, taz, left_on="DestinationName", right_on="CO_TAZID")

    df.rename(columns={"OriginName": "Origin_TAZID",
                       "DestinationName": "Destination_TAZID"},
              inplace=True)

    # Weight outputs
    df['survey_weight'] = df['Total_Time'].apply(lambda x: _survey_weight(x)).round(3)

    df['accessible_jobs'] = round(df['survey_weight'] * df['JOB'])
    df['accessible_hh'] = round(df['survey_weight'] * df['HH'])

    # keep only relevant columns
    keep_cols = ['Origin_TAZID', 'Destination_TAZID', 'Total_Time', 
                 'accessible_jobs', 'accessible_hh']
    df.drop(columns=df.columns.difference(keep_cols), inplace=True)

    # save table to input GDB
    # df.spatial.to_table(out_table + '_full') # not needed

    df_summary = df.groupby('Origin_TAZID').agg(
        accessible_jobs=pd.NamedAgg(column='accessible_jobs', aggfunc=sum),
        accessible_hh=pd.NamedAgg(column='accessible_hh', aggfunc=sum)
    )
    df_summary['CO_TAZID'] = df_summary.index.astype(int)
    taz_ato = pd.merge(df_summary, taz, on="CO_TAZID")

    taz_ato['ato'] = taz_ato.apply(
        lambda x: _ato(
            x['JOB'],
            x['accessible_jobs'],
            x['HH'],
            x['accessible_hh'],
            job_per_hh
        ),
        axis=1
    ).round()

    #taz_summary.to_csv(r'tmp\scores_summary.csv')
    taz_ato.spatial.to_table(out_table)

    # save table to input GDB
    print("Scores written to {}".format(out_table))

    ato_score = taz_ato['ato'].sum()
    print("Network ATO: {}".format(ato_score))
    
    return ato_score


def comp(gdb, driving_ato_table = 'ato_driving', 
         transit_ato_table = 'ato_transit', cycling_ato_table = 'ato_cycling',
         out_table = 'ato'):
    """Merge ATO tables for driving, transit, and cycling

    Keyword arguments:
    gdb -- 
    driving_ato_table -- 
    transit_ato_table -- 
    cycling_ato_table --
    out_table --
    """

    # location of the file geodatabase with the WFRC TAZ shapes and TAZ centroids    
    tmp_env = arcpy.env.workspace
    arcpy.env.workspace = gdb

    arr = arcpy.da.TableToNumPyArray(driving_ato_table, '*')
    driving = pd.DataFrame(arr)

    arr = arcpy.da.TableToNumPyArray(transit_ato_table, '*')
    transit = pd.DataFrame(arr)

    arr = arcpy.da.TableToNumPyArray(cycling_ato_table, '*')
    cycling = pd.DataFrame(arr)

    df = pd.merge(
        pd.merge(
            driving, 
            transit, 
            on=['CO_TAZID', 'HH', 'JOB'],
            how="left",
            suffixes=("_driving", "_transit")
        ), 
        cycling.rename(columns = {'accessible_jobs': 'accessible_jobs_cycling',
                                  'accessible_hh': 'accessible_hh_cycling',
                                  'ato': 'ato_cycling'}),
        how="left",
        on=['CO_TAZID', 'HH', 'JOB']
    )

    df['accessible_jobs'] = df[['accessible_jobs_driving',
                                'accessible_jobs_transit',
                                'accessible_jobs_cycling']].sum(axis=1)

    df['accessible_hh'] = df[['accessible_hh_driving',
                              'accessible_hh_transit',
                              'accessible_hh_cycling']].sum(axis=1)

    df['ato'] = df[['ato_driving', 'ato_transit', 'ato_cycling']].sum(axis=1)

    df[['CO_TAZID', 'accessible_jobs', 'accessible_hh', 'ato']].spatial.to_table(out_table)

    print('Composite ATO {0} written to {1}'.format(df['ato'].sum(), out_table))

    arcpy.env.workspace = tmp_env


def diff(baseline, scenario, out_table):
    """Calculate difference in ATO between two tables
    
    """

    field_list = ['CO_TAZID', 'accessible_jobs', 'accessible_hh', 'ato']

    arr = arcpy.da.TableToNumPyArray(baseline, field_list)
    baseline = pd.DataFrame(arr, columns = field_list)

    arr = arcpy.da.TableToNumPyArray(scenario, field_list)
    scenario = pd.DataFrame(arr, columns = field_list)

    df = pd.merge(
        baseline, 
        scenario, 
        on='CO_TAZID', 
        how="inner",
        suffixes=("_before", "_after")
    )

    df['diff_hh'] = df['accessible_hh_after'] - df['accessible_hh_before']
    df['diff_jobs'] = df['accessible_jobs_after'] - df['accessible_jobs_before']
    df['diff_ato'] = df['ato_after'] - df['ato_before']

    df[['CO_TAZID', 'diff_jobs', 'diff_hh', 'diff_ato']].spatial.to_table(out_table)

    print('Scenario score: {0}'.format(df['diff_ato'].sum()))
