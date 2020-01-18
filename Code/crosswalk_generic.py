## A generic code to construct your own crosswalk, from two shapefiles

import pandas as pd
import geopandas as gpd
import os

## defining variables - change the things in ALL_CAPS
origin_path = 'PATH_ORIGIN'
origin_fname = 'ORIGIN_FNAME'
origin_geoid = 'ORIGIN_GEOID'

destination_path = 'PATH_DESTINATION'
destination_fname = 'DESTINATION_FNAME'
destination_geoid = 'DESTINATION_GEOID'

output_path = 'OUTPUT_PATH'
output_fname = 'OUTPUT_FNAME'


## read in starting shapefile
os.chdir(origin_path)
shp_origin = gpd.GeoDataFrame.from_file(origin_fname)
shp_origin['area_base'] = shp_origin.area

## read in ending shapefile
os.chdir(destination_path)
shp_destination = gpd.GeoDataFrame.from_file(destination_fname)


## intersecting the file
intersect = gpd.overlay(shp_origin, shp_destination, how = 'intersection')
intersect['area'] = intersect.area

## computing weights
intersect['weight'] = intersect['area'] / intersect['area_base']

## renormalizing weights - this isn't necesary, but without it, if the shapefiles do not perfectly line up where they should, you may lose small fractions of area here and there
reweight = temp.groupby(origin_geoid)['weight'].sum().reset_index()
reweight['new_weight'] = reweight['weight']
reweight = reweight.drop('weight', axis = 1)

intersect = intersect.merge(reweight, left_on = origin_geoid, right_on = origin_geoid)
intersect['weight'] = intersect['weight'] / intersect['new_weight']

intersect = intersect.drop('new_weight', axis =1)


## keeping only relevant columns - again isn't necessary, but will help trim down the size of the crosswalk at the end
output = intersect[[origin_geoid, destination_geoid, 'weight']]


## saving output
output.to_csv(output_fname, index = False)
