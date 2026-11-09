"""Build the crosswalk from historical US counties (1790-2010) to 1990 or 2010 counties.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", working paper, 2026. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/crosswalk_county.py --end-year 2010
    python Code/crosswalk_county.py --end-year 1990 --shapefiles /path/to/Shapefiles

The NHGIS county shapefiles (US_county_<year>.shp) must sit in the Shapefiles folder, in any
subfolders, as described in Shapefiles/HowToAcquireShapeFiles.txt. The output is written to
Crosswalks/county_crosswalk_endyr_<END_YEAR>.csv.

What the script does, for each census year from 1790 to 2010 (except the reference year):
  1. Read that year's county map ("reporting map") and the reference county map.
  2. Overlay the two maps. Every piece of the result lies in exactly one historical county
     and one reference county.
  3. Divide the area of each piece by the area of its historical county. This is the weight:
     the share of the historical county that lies in that reference county.
  4. Drop pieces of 10 square meters or less. They come from small differences in how the
     maps draw the same boundary, not from real boundary changes (paper, Appendix A).
  5. Rescale the remaining weights so that the weights of each historical county sum to one.
  6. Flag whether the historical county lies in a state that was in the Union that year.
The years are then stacked into one file, with ready-made merge keys (merge_keys.py).
"""
import argparse
import glob
import os
import time

import numpy as np
import pandas as pd
import geopandas as gpd

from merge_keys import add_merge_keys

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)
YEARS = ['1790', '1800', '1810', '1820', '1830', '1840', '1850', '1860', '1870', '1880',
         '1890', '1900', '1910', '1920', '1930', '1940', '1950', '1960', '1970', '1980',
         '1990', '2000', '2010']
MIN_AREA = 10  # pieces of 10 square meters or less are dropped (paper, Appendix A)

# Columns that describe a historical county in the output, in this order.
HISTORICAL_COLS = ['NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY']


def find_shapefile(shapefile_dir, name):
    """Find the file `name` anywhere under shapefile_dir. NHGIS names the folders after each
    user's extract number (nhgis0010_..., nhgis0110_...), but the files inside are always called
    US_county_<year>.shp, so the scripts search for the file name, not the folder."""
    hits = sorted(glob.glob(os.path.join(shapefile_dir, '**', name), recursive=True))
    if not hits:
        raise FileNotFoundError(f"{name} not found under {shapefile_dir}. "
                                "See Shapefiles/HowToAcquireShapeFiles.txt.")
    if len(hits) > 1:
        raise ValueError(f"{name} found more than once under {shapefile_dir}: {hits}. Keep one copy.")
    return hits[0]


def read_year(shapefile_dir, year, state_names):
    """Read the NHGIS county map of one census year.

    All maps share one projection (USA Contiguous Albers Equal Area, NAD83), in meters,
    so the areas computed below are in square meters."""
    shp = gpd.read_file(find_shapefile(shapefile_dir, 'US_county_' + year + '.shp'))
    if year == '2010':
        shp = fix_2010(shp, state_names)
    return shp


def fix_2010(shp, state_names):
    """Give the 2010 map the column names of the other years.

    The 2010 map comes from the 2010 TIGER files and names its columns differently.
    - NHGISST becomes the NHGIS state code: the FIPS state code with a zero appended (01 -> 10).
    - NHGISCTY stays the three-digit FIPS county code (the NHGIS code would add a zero).
    - State names come from state_name_cw.csv. Puerto Rico is not in that file and drops out.
    - ICPSR codes do not exist for 2010 counties and are left empty."""
    shp = shp[['STATEFP10', 'COUNTYFP10', 'NAME10', 'geometry']].copy()
    shp = shp.rename(columns={'STATEFP10': 'NHGISST', 'COUNTYFP10': 'NHGISCTY', 'NAME10': 'NHGISNAM'})
    shp['NHGISST'] = (shp['NHGISST'] + '0').astype(int)
    shp = shp.merge(state_names, on='NHGISST')
    shp['ICPSRCTY'] = np.nan
    shp['ICPSRST'] = np.nan
    return shp


def crosswalk_one_year(shp, shp_end, year, end_cols, states):
    """Crosswalk from one census year's counties to the reference map.

    shp:      that year's county map
    shp_end:  the reference map (1990 or 2010 counties, or 1990 commuting zones)
    end_cols: the reference map's ID and name columns to keep
    states:   states_union.csv, which says which states were in the Union in each year"""
    shp['Year'] = year

    # Area of each historical county, measured before the overlay.
    shp['area_base'] = shp.area

    # Overlay: one row for each piece that lies in one historical county and one reference unit.
    temp = gpd.overlay(shp, shp_end, how='intersection')

    # Weight: the share of the historical county's area that lies in this reference unit.
    temp['area'] = temp.area
    temp['weight'] = temp['area'] / temp['area_base']
    temp = temp[['Year'] + HISTORICAL_COLS + ['area_base'] + end_cols + ['area', 'weight']]

    # Drop slivers: pieces of 10 square meters or less.
    temp = temp[temp['area'] > MIN_AREA]

    # Rescale so the weights of each historical county sum to one. This spreads the area lost
    # to dropped slivers, and to places where the two maps' coastlines differ, over the pieces kept.
    temp['weight'] = temp['weight'] / temp.groupby(['NHGISCTY', 'NHGISST'])['weight'].transform('sum')

    # US_STATE = 1 if the historical county lies in a state that was part of the Union in this year.
    # states_union.csv has one column per census year with 1 for the states in the Union.
    in_union = states.loc[states[year] == 1, 'State'].str.strip()
    temp['US_STATE'] = temp['STATENAM'].isin(in_union).astype(int)
    return pd.DataFrame(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--end-year', default='2010', choices=['1990', '2010'])
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    end_year = args.end_year

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    states = pd.read_csv(os.path.join(CODE_DIR, 'states_union.csv'))

    # The reference map. Its columns get the reference year as a suffix (NHGISST_2010, ...)
    # so they stay apart from the historical county's columns after the overlay.
    shp_end = read_year(args.shapefiles, end_year, state_names)
    shp_end.columns = [c if c == 'geometry' else c + '_' + end_year for c in shp_end.columns]
    end_cols = [c + '_' + end_year for c in HISTORICAL_COLS]

    # One crosswalk per census year. The reference year itself is skipped: it maps to itself.
    parts = []
    for year in [y for y in YEARS if y != end_year]:
        start = time.time()
        shp = read_year(args.shapefiles, year, state_names)
        parts.append(crosswalk_one_year(shp, shp_end, year, end_cols, states))
        print(year, round(time.time() - start, 1), 'seconds', flush=True)

    # Stack the years, add the merge keys (GISJOIN, FIPS codes) and save.
    out = os.path.join(args.out, 'county_crosswalk_endyr_' + end_year + '.csv')
    add_merge_keys(pd.concat(parts, ignore_index=True), end_year).to_csv(out, index=False)
    print('saved', out)


if __name__ == '__main__':
    main()
