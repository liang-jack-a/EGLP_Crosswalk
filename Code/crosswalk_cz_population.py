"""Add the livable-area and population-based weights to the commuting zone crosswalk.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", NBER WP 26770. www.fpeckert.me/eglp

Usage (from the repository root), after crosswalk_cz.py, livable_land.py and towns.py:
    python Code/crosswalk_cz_population.py
    python Code/crosswalk_cz_population.py --shapefiles /path/to/Shapefiles

The steps are those of crosswalk_county_population.py, with the 1990 commuting zones as the reference
map. Commuting zones are unions of 1990 counties; each cell of the grid gets the zone of its 1990 county.
Adds weight_livable and weight_population to Crosswalks/cz_crosswalk.csv, after weight.
"""
import argparse
import os

import pandas as pd

from crosswalk_county import find_shapefile
from population_weights import people_by_piece, drop_border_strips, weights, add_to_crosswalk

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--inputs', default=os.path.join(ROOT, 'Inputs'))
    parser.add_argument('--intermediate', default=os.path.join(ROOT, 'Intermediate'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    d = people_by_piece(args.shapefiles, state_names, os.path.join(args.intermediate, 'livable_land.tif'),
                        os.path.join(args.inputs, 'nhgis', 'nhgis_ts_nominal_county.csv'),
                        os.path.join(args.intermediate, 'towns.gpkg'), 'cz',
                        cz_shp=find_shapefile(args.shapefiles, 'cz1990.shp'))
    w = weights(drop_border_strips(d), 'cz')
    add_to_crosswalk(os.path.join(args.out, 'cz_crosswalk.csv'), w, 'cz')


if __name__ == '__main__':
    main()
