# Score Scenarios

'''Run the cells below to score the configured scenarios. Any unscored scenarios will be scored.

To re-score a scenario, open its corresponding file geodatabase and delete its `scores` and `scores_summary` table.'''

print('--begin score')

import sys
import os
import arcpy

import numpy as np
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor

src = os.path.join(os.path.abspath("."), 'src')
if src not in sys.path:
    sys.path.append(src)
    
from src.ato_tools import ato

if 'ato_tools' in sys.modules:
    import importlib
    importlib.reload(ato)

base_path = os.path.abspath(".")
baseline_gdb = "baseline.gdb"
equity_taz = pd.read_csv('equity_taz.csv')
equity_taz['efa'] = equity_taz[['poverty', 'minority', 'zero_car']].max(axis=1)
taz_table = pd.DataFrame(arcpy.da.TableToNumPyArray(r'baseline.gdb\taz_table', '*'))


print('--building list of scenarios')
scenarios = list()
for mode in ['Cycling', 'Driving', 'Transit', 'Land_Use']:
    for file in os.listdir(os.path.join('scenario', mode)):
        d = os.path.join(base_path, os.path.join('scenario', mode), file)
        if os.path.isdir(d) and d.endswith('.gdb'):
            scenarios.append({"name": file[:-4],
                              'gdb': d,
                              'mode': mode})
            
modal_scenarios = [x for x in scenarios if x['mode'] != 'Land_Use']
land_use_scenarios = [x for x in scenarios if x['mode'] == 'Land_Use']

### Calculate skim matrices for new mode scenarios

'''In the event that the cell below produces a 'Network Travel Times are Zero' error, rebuild the network,
e.g. `ato.build('scenario/Transit/box_elder_express.gdb/NetworkDataset/NetworkDataset_ND')`

The cell below should take:

* ~20 minutes per roadway scenario
* ~5 minutes per transit scenario
* ~5 minutes per cycling scenario'''

# this could be: while there is no error, run below, else rebuild network

# calculate skim matrices for new scenarios
for scenario in modal_scenarios:
    print(f'--skimming {scenario}')
    if not arcpy.Exists(os.path.join(scenario['gdb'], "skim_matrix")):
        ato.skim(
            # need to check if this exist first
            nd = os.path.join(scenario['gdb'], r'NetworkDataset\NetworkDataset_ND'),
            mode = scenario['mode'],
            centroids = r'baseline.gdb\taz_centroids',
            out_table = os.path.join(scenario['gdb'], r"skim_matrix")
        )

'''Just to reiterate, if the loop above fails due to an invalid network (this is caused by a bug in Esri's software, not a problem with your network), you can correct the issue by rebuilding the network.

Insert a new cell and run `ato.build()` on the full network dataset path, e.g. 

```python
ato.build('scenario/Transit/ogden_local_bus.gdb/NetworkDataset/NetworkDataset_ND')
```'''

# score mode projects
for scenario in modal_scenarios:
    print(f'--scoring {scenario}')
    if not arcpy.Exists(os.path.join(scenario['gdb'], "ato")):
        ato.score(
            skim_matrix = os.path.join(scenario['gdb'], r"skim_matrix"),
            taz_table = r'baseline.gdb\taz_table',
            out_table = os.path.join(scenario['gdb'], r"ato")
        )
for scenario in land_use_scenarios:
    # score land use projects using the baseline skim matrix 
    # since changes in land use do not change travel times
    print(f'--scoring {scenario}')
    if scenario['mode'] == 'Land_Use' and not arcpy.Exists(os.path.join(scenario['gdb'], "ato_driving")):
        for mode in ['driving', 'transit', 'cycling']:
            ato.score(
                skim_matrix = os.path.join(baseline_gdb, "skim_" + mode),
                taz_table = os.path.join(scenario['gdb'], r"taz_table"),
                out_table = os.path.join(scenario['gdb'], r"ato_" + mode),
                job_per_hh = 1.80875
            )


'''
## Tabulate Scores Across Scenarios

The cells below read in the scores from all scored scenarios, calculate weighted average scenario scores, and combine these scores into summary tables:

* Transportation Network Changes: `scenario\scenario_scores.csv`
* Land Use Changes: `scenario\land_use_scenario_scores.csv`

Scores for individual projects can be extracted from the `scores_summary` table within each file geodatabase.
'''

### Tabulate Mode Scenario Scores
print('--tabulating scores')
scenario_scores = pd.DataFrame(columns = 
    ['name', 'mode', 'hh_access', 'jobs_access', 'comp_access',
     'pov_accessible_jobs', 'minority_accessible_jobs', 
     'zero_car_accessible_jobs', 'efa_accessible_jobs']
)

for scenario in modal_scenarios:
    
    mode = scenario['mode']
    
    if mode == 'Driving':
        baseline = r'baseline.gdb\ato_driving'
    elif mode == 'Transit':
        baseline = r'baseline.gdb\ato_transit'
    elif mode == 'Cycling':
        baseline = r'baseline.gdb\ato_cycling'
    
    scores_table = os.path.join(scenario['gdb'], 'scores')
    
    if not arcpy.Exists(scores_table):
        ato.diff(
            baseline = baseline,
            scenario = os.path.join(scenario['gdb'], 'ato'),
            out_table = scores_table
        )
    
    df = pd.DataFrame(arcpy.da.TableToNumPyArray(scores_table, '*'))

    df = pd.merge(
        df, 
        equity_taz, 
        on='taz_id', 
        how="left"
    )

    df = pd.merge(
        df, 
        taz_table, 
        on='taz_id', 
        how="left"
    )
    
    df.fillna(0, inplace=True)
    
    vals = {
        "name": scenario['name'],
        'mode': mode,
        "hh_access": np.average(df['diff_hh'], weights=df['job']),
        "jobs_access": np.average(df['diff_jobs'], weights=df['hh']),
        "comp_access": np.average(df['diff_ato'], weights=(df['job'] + df['hh'])),
        'pov_accessible_jobs': np.average(
            df['diff_jobs'] * df['poverty'], 
            weights=(df['hh'] * df['poverty'])
        ),
        'minority_accessible_jobs': np.average(
            df['diff_jobs'] * df['minority'], 
            weights=(df['hh'] * df['minority'])
        ),
        'zero_car_accessible_jobs': np.average(
            df['diff_jobs'] * df['zero_car'], 
            weights=(df['hh'] * df['zero_car'])
        ),
        'efa_accessible_jobs': np.average(
            df['diff_jobs'] * df['efa'], 
            weights=(df['hh'] * df['efa'])
        )
    }
    vals['hh_access'] = round(vals['hh_access'], 1)
    vals['jobs_access'] = round(vals['jobs_access'], 1)
    vals['comp_access'] = round(vals['comp_access'], 1)
    vals['pov_accessible_jobs'] = round(vals['pov_accessible_jobs'], 1)
    vals['minority_accessible_jobs'] = round(vals['minority_accessible_jobs'], 1)
    vals['zero_car_accessible_jobs'] = round(vals['zero_car_accessible_jobs'], 1)
    vals['efa_accessible_jobs'] = round(vals['efa_accessible_jobs'], 1)
    
    
    # scenario_scores = scenario_scores.append(vals, ignore_index=True)
    scenario_scores = pd.concat([scenario_scores, pd.DataFrame([vals])], ignore_index=True)

### Tabulate Land Use Scenario Scores

land_use_scenario_scores = pd.DataFrame(columns = 
    ['Name', 'driving_comp', 'cycling_comp', 'transit_comp', 
     'cycling_to_auto', 'transit_to_auto']
)

for scenario in land_use_scenarios:
    scores = {}

    for mode in ['driving', 'transit', 'cycling']:
        baseline = os.path.join('baseline.gdb', 'ato_' + mode)
        scenario_ato_scores = os.path.join(scenario['gdb'], 'ato_' + mode)
        
        scores_table = os.path.join(scenario['gdb'], 'scores_' + mode)
        
        # store only new scores tables
        if not arcpy.Exists(scores_table):
            ato.diff(
                baseline, 
                scenario_ato_scores,
                scores_table
            )
        
        df = pd.DataFrame(arcpy.da.TableToNumPyArray(scores_table, '*'))

        df = pd.merge(
            df, 
            taz_table, 
            on='CO_TAZID', 
            how="left"
        )
        
        df.fillna(0, inplace=True)
        
        scores[mode] = np.average(
            df['diff_jobs'], 
            weights=(df['JOB'] + df['HH'])
        )
    
    vals = {
        "Name": scenario['name'],
        'driving_comp': round(scores['driving'], 1),
        'cycling_comp': round(scores['cycling'], 1),
        'transit_comp': round(scores['transit'], 1), 
        'cycling_to_auto': round(scores['cycling'] / scores['driving'], 2),
        'transit_to_auto': round(scores['transit'] / scores['driving'], 2)
    }
    
    # land_use_scenario_scores = land_use_scenario_scores.append(vals, ignore_index=True)
    land_use_scenario_scores = pd.concat([land_use_scenario_scores, vals], ignore_index=True)



land_use_scenario_scores.to_csv(r'scenario\land_use_scenario_scores.csv')
scenario_scores.to_csv(r'scenario\scenario_scores.csv')



print('--score complete!')





