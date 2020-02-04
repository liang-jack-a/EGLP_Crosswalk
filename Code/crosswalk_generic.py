## A generic code to construct your own crosswalk, from two shapefiles

import pandas as pd
import geopandas as gpd
import os

## defining variables - change the things in ALL_CAPS
reporting_path = 'PATH_REPORTING'
reporting_fname = 'REPORTING_FNAME'
reporting_geoid = 'REPORTING_GEOID'

reference_path = 'PATH_REFERENCE'
reference_fname = 'REFERENCE_FNAME'
reference_geoid = 'REFERENCE_GEOID'

output_path = 'OUTPUT_PATH'
output_fname = 'OUTPUT_FNAME'


## read in starting shapefile
os.chdir(reporting_path)
shp_reporting = gpd.GeoDataFrame.from_file(reporting_fname)
shp_reporting['area_base'] = shp_reporting.area

## read in ending shapefile
os.chdir(reference_path)
shp_reference = gpd.GeoDataFrame.from_file(reference_fname)


## intersecting the file
intersect = gpd.overlay(shp_reporting, shp_reference, how = 'intersection')
intersect['area'] = intersect.area

## computing weights
intersect['weight'] = intersect['area'] / intersect['area_base']

## renormalizing weights - this isn't necesary, but without it, if the shapefiles do not perfectly line up where they should, you may lose small fractions of area here and there
reweight = temp.groupby(reporting_geoid)['weight'].sum().reset_index()
reweight['new_weight'] = reweight['weight']
reweight = reweight.drop('weight', axis = 1)

intersect = intersect.merge(reweight, left_on = reporting_geoid, right_on = reporting_geoid)
intersect['weight'] = intersect['weight'] / intersect['new_weight']

intersect = intersect.drop('new_weight', axis =1)


## keeping only relevant columns - again isn't necessary, but will help trim down the size of the crosswalk at the end
output = intersect[[reporting_geoid, reference_geoid, 'weight']]


## saving output
output.to_csv(output_fname, index = False)
