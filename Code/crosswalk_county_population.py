"""Add the livable-area and population-based weights to the county crosswalk (1990 or 2010 counties).

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", working paper, 2026. www.fpeckert.me/eglp

Usage (from the repository root), after crosswalk_county.py, livable_land.py and towns.py:
    python Code/crosswalk_county_population.py --end-year 2010
    python Code/crosswalk_county_population.py --end-year 1990 --shapefiles /path/to/Shapefiles

Reads Crosswalks/county_crosswalk_endyr_<END_YEAR>.csv, Intermediate/livable_land.tif and
Intermediate/towns.gpkg, the NHGIS county shapefiles (Shapefiles folder) and the NHGIS county population
table (Inputs folder, see Inputs/HowToAcquireInputs.txt). Adds two columns to the crosswalk, after weight:
  weight_livable     the share of the historical county's livable land in the reference county
  weight_population  the share of the historical county's people in the reference county
The column weight stays the area-based weight. The steps are described in population_weights.py.
The two new columns are empty for Alaska and Hawaii, which the map of livable land does not cover.
"""
import argparse
import os

import pandas as pd

from population_weights import people_by_piece, drop_border_strips, weights, add_to_crosswalk

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--end-year', default='2010', choices=['1990', '2010'])
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--inputs', default=os.path.join(ROOT, 'Inputs'))
    parser.add_argument('--intermediate', default=os.path.join(ROOT, 'Intermediate'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Crosswalks'))
    args = parser.parse_args()
    end_year = args.end_year

    state_names = pd.read_csv(os.path.join(CODE_DIR, 'state_name_cw.csv'))
    d = people_by_piece(args.shapefiles, state_names, os.path.join(args.intermediate, 'livable_land.tif'),
                        os.path.join(args.inputs, 'nhgis', 'nhgis_ts_nominal_county.csv'),
                        os.path.join(args.intermediate, 'towns.gpkg'), end_year)
    w = weights(drop_border_strips(d), end_year)
    add_to_crosswalk(os.path.join(args.out, 'county_crosswalk_endyr_' + end_year + '.csv'), w, 'GISJOIN_' + end_year)


if __name__ == '__main__':
    main()
