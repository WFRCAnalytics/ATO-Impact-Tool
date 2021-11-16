import arcpy
import os
import pandas as pd

centroids = os.path.join(os.path.abspath("."), r"shp\taz_wfrc.gdb\taz_centroids_sample")

def test_network(nd_path, mode = "Driving"):
    print("Testing integrity of network " + nd_path)
    nd_layer_name = "tmp_test"
    arcpy.nax.MakeNetworkDatasetLayer(nd_path, nd_layer_name)
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
