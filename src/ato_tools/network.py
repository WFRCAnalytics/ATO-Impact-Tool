import arcpy
import os
import pandas as pd
import time

centroids = os.path.join(os.path.abspath("."), r"shp\taz_wfrc.gdb\taz_centroids_sample")

def test(nd, mode = "Driving"):
    print("Testing integrity of network {0} for {1}".format(nd, mode))
    nd_layer_name = "tmp_test"
    arcpy.nax.MakeNetworkDatasetLayer(nd, nd_layer_name)
    odcm = arcpy.nax.OriginDestinationCostMatrix(nd_layer_name)
    odcm.travelMode = mode
    odcm.defaultImpedanceCutoff = 60
    odcm.lineShapeType = arcpy.nax.LineShapeType.NoLine
    odcm.load(arcpy.nax.OriginDestinationCostMatrixInputDataType.Origins, centroids)
    odcm.load(arcpy.nax.OriginDestinationCostMatrixInputDataType.Destinations, centroids)
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
    else:
        print("Network validation: PASS")
        return True

def build(nd):
    """
    Add a routine here to time the build process. Raise a warning
    when < 10 seconds - or force a test / rebuild cycle
    """
    if arcpy.Exists(nd):
        arcpy.management.Delete(nd)

    target_gdb = nd[:-len(r'\NetworkDataset\NetworkDataset_ND')]
    print("Target GDB: {}".format(target_gdb))
    
    # create network dataset from template
    arcpy.nax.CreateNetworkDatasetFromTemplate(
        os.path.join(os.path.abspath("."), "template.xml"),                 
        os.path.join(target_gdb, "NetworkDataset")
    )

    start = time.time()

    arcpy.nax.BuildNetwork(nd)

    end = time.time()

    duration = end-start
    print("Network Build Time (seconds): {}".format(duration))
    if duration < 10:
        print("Warning: abnormally short build duration. Verify network validity.")