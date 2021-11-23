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


## Conda Run
Run "cmd"
Run `"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat"` then `exit()`
Then run `activate`
then cd to c:\wfrc\ato and run `jupyter notebook`