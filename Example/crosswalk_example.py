"""A simple example: map 1900 county population from NHGIS to 2010 counties.

Run from anywhere:  python Example/crosswalk_example.py
It reads the 2010 county crosswalk from the Crosswalks folder and Example/Data/nhgis0014_ds31_1900_county.csv
and writes Example/example_output.csv.
"""
import os

import pandas as pd

example_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(example_dir)

## reading in data
# the file is called county_crosswalk_endyr_2010.csv on GitHub and eglp_county_crosswalk_endyr_2010.csv
# on the website; put either one in a Crosswalks folder next to the Example folder
for name in ['county_crosswalk_endyr_2010.csv', 'eglp_county_crosswalk_endyr_2010.csv']:
    cw_file = os.path.join(root, 'Crosswalks', name)
    if os.path.exists(cw_file):
        break
cw = pd.read_csv(cw_file, low_memory=False)
pop = pd.read_csv(os.path.join(example_dir, 'Data', 'nhgis0014_ds31_1900_county.csv'), encoding='latin-1')

## keeping only the relevant year, 1900
cw = cw[cw['Year'] == 1900]

## setting up the county correspondence:
## it is "STATEA" and "COUNTYA" in pop, and "NHGISST" and "NHGISCTY" in cw
pop['id'] = pop['STATEA'].astype(int) * 10000 + pop['COUNTYA'].astype(int)
cw['id'] = cw['NHGISST'].astype(int) * 10000 + cw['NHGISCTY'].astype(int)

## a few territories in the population file have codes that are not in the NHGIS maps
pop = pop[pop['id'].isin(cw['id'])]
print('1900 population before mapping:', pop['AYM001'].sum())
merged = pop.merge(cw, on='id', how='outer')

## splitting each 1900 county's population across 2010 counties by the weights
merged['Population'] = merged['weight'] * merged['AYM001']

## aggregating to 2010 counties
output = merged.groupby(['NHGISST_2010', 'NHGISCTY_2010', 'STATENAM_2010', 'NHGISNAM_2010'])['Population'].sum().reset_index()
output.to_csv(os.path.join(example_dir, 'example_output.csv'), index=False)
print('1900 population after mapping to 2010 counties:', output['Population'].sum())
