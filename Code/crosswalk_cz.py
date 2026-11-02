"""Build the crosswalk from historical US counties (1790-2010) to 1990 commuting zones.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", NBER WP 26770. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/crosswalk_cz.py
    python Code/crosswalk_cz.py --shapefiles /path/to/Shapefiles

The NHGIS county shapefiles and the commuting zone shapefile (cz1990_shapefile, from
https://healthinequality.org/data/) must sit in the Shapefiles folder, as described in
Shapefiles/HowToAcquireShapeFiles.txt. The output is written to Crosswalks/cz_crosswalk.csv.
"""
import argparse
import os
import time

import pandas as pd
import geopandas as gpd

from crosswalk_county import YEARS, MIN_AREA, read_year

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)

# The commuting zone shapefile is in longitude-latitude (EPSG:4326). The NHGIS shapefiles use
# the USA Contiguous Albers Equal Area projection (NAD83). Reproject the commuting zones to it.
NHGIS_ALBERS = {'proj': 'aea', 'lat_1': 29.5, 'lat_2': 45.5, 'lat_0': 37.5, 'lon_0': -96,
                'x_0': 0, 'y_0': 0, 'datum': 'NAD83', 'units': 'm', 'no_defs': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    states = pd.read_csv(os.path.join(CODE_DIR, 'states_union.csv'))

    shp_end = gpd.read_file(os.path.join(args.shapefiles, 'cz1990_shapefile', 'cz1990.shp'))
    shp_end = shp_end.to_crs(NHGIS_ALBERS)

    parts = []
    for year in YEARS:
        start = time.time()
        shp = read_year(args.shapefiles, year, state_names)
        shp['Year'] = year
        shp['area_base'] = shp.area
        temp = gpd.overlay(shp, shp_end, how='intersection')
        temp['area'] = temp.area
        temp['weight'] = temp['area'] / temp['area_base']
        temp = temp[['Year', 'NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY',
                     'area_base', 'cz', 'area', 'weight']]
        # drop slivers of 10 square meters or less, as in the county crosswalks
        temp = temp[temp['area'] > MIN_AREA]
        temp['weight'] = temp['weight'] / temp.groupby(['NHGISCTY', 'NHGISST'])['weight'].transform('sum')
        in_union = states.loc[states[year] == 1, 'State'].str.strip()
        temp['US_STATE'] = temp['STATENAM'].isin(in_union).astype(int)
        parts.append(pd.DataFrame(temp))
        print(year, round(time.time() - start, 1), 'seconds', flush=True)

    out = os.path.join(args.out, 'cz_crosswalk.csv')
    pd.concat(parts, ignore_index=True).to_csv(out, index=False)
    print('saved', out)


if __name__ == '__main__':
    main()
