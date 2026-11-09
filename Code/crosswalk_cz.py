"""Build the crosswalk from historical US counties (1790-2010) to 1990 commuting zones.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", working paper, 2026. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/crosswalk_cz.py
    python Code/crosswalk_cz.py --shapefiles /path/to/Shapefiles

The NHGIS county shapefiles and the commuting zone shapefile (cz1990_shapefile, from
https://healthinequality.org/data/) must sit in the Shapefiles folder (in any subfolders), as described in
Shapefiles/HowToAcquireShapeFiles.txt. The output is written to Crosswalks/cz_crosswalk.csv.

The steps are those of crosswalk_county.py, with the 1990 commuting zones as the reference
map. Every census year from 1790 to 2010 is included, 1990 and 2010 too.
"""
import argparse
import os
import time

import pandas as pd
import geopandas as gpd

from crosswalk_county import YEARS, find_shapefile, read_year, crosswalk_one_year
from merge_keys import add_merge_keys

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)

# The commuting zone shapefile is in longitude and latitude (EPSG:4326). The NHGIS maps use the
# USA Contiguous Albers Equal Area projection (NAD83), in meters. The commuting zones are moved to
# that projection, so that the two maps line up and areas come out in square meters.
NHGIS_ALBERS = {'proj': 'aea', 'lat_1': 29.5, 'lat_2': 45.5, 'lat_0': 37.5, 'lon_0': -96,
                'x_0': 0, 'y_0': 0, 'datum': 'NAD83', 'units': 'm', 'no_defs': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    states = pd.read_csv(os.path.join(CODE_DIR, 'states_union.csv'))

    # The reference map: 1990 commuting zones, identified by the column cz.
    shp_end = gpd.read_file(find_shapefile(args.shapefiles, 'cz1990.shp'))
    shp_end = shp_end.to_crs(NHGIS_ALBERS)

    # One crosswalk per census year, computed exactly as for the county crosswalks.
    parts = []
    for year in YEARS:
        start = time.time()
        shp = read_year(args.shapefiles, year, state_names)
        parts.append(crosswalk_one_year(shp, shp_end, year, ['cz'], states))
        print(year, round(time.time() - start, 1), 'seconds', flush=True)

    # Stack the years, add the merge key GISJOIN and save.
    out = os.path.join(args.out, 'cz_crosswalk.csv')
    add_merge_keys(pd.concat(parts, ignore_index=True)).to_csv(out, index=False)
    print('saved', out)


if __name__ == '__main__':
    main()
