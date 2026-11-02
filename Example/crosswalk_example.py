"""Map 1900 county population from NHGIS to 2010 counties with the EGLP crosswalk.

Run from anywhere:  python Example/crosswalk_example.py
Reads  Crosswalks/county_crosswalk_endyr_2010.csv and Example/Data/nhgis0014_ds31_1900_county.csv
Writes Example/example_output.csv
"""
import os

import pandas as pd

example_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(example_dir)

# 1. The crosswalk: keep the rows for the year of the data.
#    (On the website the file is called eglp_county_crosswalk_endyr_2010.csv.)
for name in ['county_crosswalk_endyr_2010.csv', 'eglp_county_crosswalk_endyr_2010.csv']:
    cw_file = os.path.join(root, 'Crosswalks', name)
    if os.path.exists(cw_file):
        break
cw = pd.read_csv(cw_file, dtype={'GISJOIN': str, 'FIPS_2010': str}, low_memory=False)
cw = cw[cw['Year'] == 1900]

# 2. The data: NHGIS county population in 1900. Every NHGIS extract has a GISJOIN column.
pop = pd.read_csv(os.path.join(example_dir, 'Data', 'nhgis0014_ds31_1900_county.csv'), encoding='latin-1', dtype={'GISJOIN': str})
print('1900 population before mapping:', pop['AYM001'].sum())

# 3. Merge on GISJOIN. Each 1900 county gets one row per 2010 county it overlaps.
#    A few territories in the population file are not on the NHGIS 1900 map; they drop out here.
merged = pop.merge(cw, on='GISJOIN', how='inner')

# 4. Split each county's population by the weights and add up within 2010 counties.
merged['population'] = merged['AYM001'] * merged['weight']
output = merged.groupby(['FIPS_2010', 'STATENAM_2010', 'NHGISNAM_2010'], as_index=False)['population'].sum()
output.to_csv(os.path.join(example_dir, 'example_output.csv'), index=False)
print('1900 population after mapping to 2010 counties:', output['population'].sum())
