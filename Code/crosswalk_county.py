"""Build the crosswalk from historical US counties (1790-2010) to 1990 or 2010 counties.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", NBER WP 26770. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/crosswalk_county.py --end-year 2010
    python Code/crosswalk_county.py --end-year 1990 --shapefiles /path/to/Shapefiles

The NHGIS county shapefiles must sit in the Shapefiles folder, one subfolder per year,
as described in Shapefiles/HowToAcquireShapeFiles.txt. The output is written to
Crosswalks/county_crosswalk_endyr_<END_YEAR>.csv.
"""
import argparse
import os
import time

import numpy as np
import pandas as pd
import geopandas as gpd

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)
YEARS = ['1790', '1800', '1810', '1820', '1830', '1840', '1850', '1860', '1870', '1880',
         '1890', '1900', '1910', '1920', '1930', '1940', '1950', '1960', '1970', '1980',
         '1990', '2000', '2010']
MIN_AREA = 10  # intersections of 10 square meters or less are dropped (paper, Appendix A)


def read_year(shapefile_dir, year, state_names):
    """Read the NHGIS county shapefile for one decade."""
    folder = os.path.join(shapefile_dir, 'nhgis0010_shapefile_tl2000_us_county_' + year)
    shp = gpd.read_file(os.path.join(folder, 'US_county_' + year + '.shp'))
    if year == '2010':
        shp = fix_2010(shp, state_names)
    return shp


def fix_2010(shp, state_names):
    """The 2010 shapefile uses different column names. Rename them to the NHGIS names
    used in the other years. Puerto Rico drops out because it is not in state_name_cw.csv.
    NHGISST becomes the NHGIS state code (FIPS with a zero appended); NHGISCTY stays the
    three-digit FIPS county code; ICPSR codes do not exist for 2010 and are left empty."""
    shp = shp[['STATEFP10', 'COUNTYFP10', 'NAME10', 'geometry']]
    shp = shp.rename(columns={'STATEFP10': 'NHGISST', 'COUNTYFP10': 'NHGISCTY', 'NAME10': 'NHGISNAM'})
    shp['NHGISST'] = (shp['NHGISST'] + '0').astype(int)
    shp = shp.merge(state_names, on='NHGISST')
    shp['ICPSRCTY'] = np.nan
    shp['ICPSRST'] = np.nan
    return shp


def crosswalk_one_year(shp, shp_end, year, end_cols, states):
    """Intersect one decade's counties with the reference map and compute area weights."""
    shp['Year'] = year
    shp['area_base'] = shp.area
    temp = gpd.overlay(shp, shp_end, how='intersection')
    temp['area'] = temp.area
    temp['weight'] = temp['area'] / temp['area_base']
    temp = temp[['Year', 'NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY',
                 'area_base'] + end_cols + ['area', 'weight']]
    temp = temp[temp['area'] > MIN_AREA]
    # renormalize so that the weights of each historical county sum to one
    temp['weight'] = temp['weight'] / temp.groupby(['NHGISCTY', 'NHGISST'])['weight'].transform('sum')
    # indicator for counties in states that were part of the Union in that year
    in_union = states.loc[states[year] == 1, 'State'].str.strip()
    temp['US_STATE'] = temp['STATENAM'].isin(in_union).astype(int)
    return pd.DataFrame(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--end-year', default='2010', choices=['1990', '2010'])
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()
    end_year = args.end_year

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    states = pd.read_csv(os.path.join(CODE_DIR, 'states_union.csv'))

    shp_end = read_year(args.shapefiles, end_year, state_names)
    shp_end.columns = [c if c == 'geometry' else c + '_' + end_year for c in shp_end.columns]
    end_cols = [c + '_' + end_year for c in
                ['NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY']]

    parts = []
    for year in [y for y in YEARS if y != end_year]:
        start = time.time()
        shp = read_year(args.shapefiles, year, state_names)
        parts.append(crosswalk_one_year(shp, shp_end, year, end_cols, states))
        print(year, round(time.time() - start, 1), 'seconds', flush=True)

    out = os.path.join(args.out, 'county_crosswalk_endyr_' + end_year + '.csv')
    pd.concat(parts, ignore_index=True).to_csv(out, index=False)
    print('saved', out)


if __name__ == '__main__':
    main()
