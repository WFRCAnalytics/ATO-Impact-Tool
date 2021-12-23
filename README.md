# ATO Impacts Tool

Tool Author: Mark Egge (egge@highstreetconsulting.com)

A Network Analyst based tool for assessing changes in Access to Opportunity (ATO) resulting from regional mobility investments.

## Motivation
A tool for calculating access to opportunity (ATO) as defined and implemented by WFRC: the number of jobs and households "accessible" to a given traffic analysis zone (TAZ) where nearer jobs and households count more than jobs and households further away. 

ATO can be calculated for the road and transit networks by estimating travel times (via car or transit) between TAZs and then weighting the number of nearby jobs and households by a travel-time decay curve. The result is an estimate for each TAZ of the number of jobs and households "accessible" from a given TAZ. Individual TAZ access can be summed across the region for an estimated measure of access. The impacts of projects that improve mobility (and thereby accessibility) are estimated by assigning estimated reductions in travel times along calculated routes and tabulating the increase in the number of jobs and households accessible within given travel times.

## Requirements
The tool is implemented through Esri ArcGIS Pro using Python and Jupyter Notebooks. The tool primarily relyies on the Network Analyst extension and arcpy.

## Scoring Projects
![Process Flow](doc/process_flow.png)

1) Run [1_network_setup.ipynb] once. This sets everything up, including baseline scores and the template network dataset that will be modified for the scenarios. 
2) For each project, step through the appropriate 3_*.ipynb notebook corresponding to the appropriate mode. I find this take 5 – 15 minutes per project, depending on the complexity of the project.
3) Then, run [4_score.ipynb]. This notebook walks through all of the modified scenario networks in the scenario folder and scores each, writing the output results to tables within the file geodatabase. The “scores_summary” table contains the TAZ-level results. If a file geodatabase already contains a “scores” table it is skipped. Then, the script summarizes the ATO improvement scores for all scored scenarios. The whole process takes about 12 minutes per “auto” project and 4 minutes per “transit” project. 

In theory, an analyst or planner could quickly create scenario networks for a bunch of projects, and then let the scoring notebook run overnight.

## Conda Run
Run "cmd"
Run `"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat"` then `exit()`
Then run `activate`
then cd to c:\wfrc\ato and run `jupyter notebook`

Network analyst has a bug... sometimes impedance values get mismatched.


## Invalid Network Travel Times
There is an error in Esri's Network Analyst suite that occassionally causes field values in a network dataset to get transposed between fields, resulting in nonsensical impedance values (refer to Esri Case #02899742). This project includes an embedded diagnostic to detect invalid networks.

The `test` function tests for a correct network build by solving a simple routing problem between two points defined in `shp\test_points\test_points.shp`. If these points are not located within the service area of the network dataset, the test will fail.



In general, if the network dataset fails, the cure is simply to rebuild the network dataset using `ato.build(nd)`.