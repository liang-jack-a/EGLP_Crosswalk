import pandas as pd
import geopandas as gpd
import os
from os.path import join,split
import time

import numpy as np

path = split(__file__)[0]
root = split(path)[0]

os.chdir(path)


## setting up the dataframe
master_df = gpd.GeoDataFrame()

## the 2010 shape file is slightly different (column names), so coding in a fix
## note I remove puerto rico from the 2010 shapefile
def append_0(string):
    return string + '0'

cw = pd.read_csv('state_name_cw.csv')

## reading in state formally a state indicator
states = pd.read_csv('states_union.csv')


def fix_2010(shp, cw = cw):
    shp = shp[['STATEFP10', 'COUNTYFP10', 'NAME10', 'geometry']]
    shp = shp.rename(columns = {'STATEFP10': 'NHGISST', 'COUNTYFP10': 'NHGISCTY', 'NAME10': 'NHGISNAM'})
    shp['NHGISST'] = shp['NHGISST'].apply(append_0).astype(int)
    shp = shp.merge(cw, left_on = 'NHGISST', right_on = 'NHGISST')
    shp['ICPSRCTY'] = np.nan
    shp['ICPSRST'] = np.nan
    return shp



## reading the cz shapefile
os.chdir(join(root,"Shapefiles","cz1990_shapefile"))
shp_end = gpd.GeoDataFrame.from_file('cz1990.shp')
    
## fixing the projection
shp_end = shp_end.to_crs({'proj': 'aea',
 'lat_1': 29.5,
 'lat_2': 45.5,
 'lat_0': 37.5,
 'lon_0': -96,
 'x_0': 0,
 'y_0': 0,
 'datum': 'NAD83',
 'units': 'm',
 'no_defs': True})
## looping through other years
other_years = ['1790', '1800', '1810', '1820', '1830', '1840', 
             '1850', '1860', '1870', '1880', '1890', '1900', '1910',
             '1920', '1930', '1940', '1950', '1960', '1970',
             '1980', '1990', '2000', '2010']

for year in other_years:
    
    start = time.time() ## for testing purposes
    
    ## reading in shapefiles
    os.chdir(join(root,"Shapefiles","nhgis0010_shapefile_tl2000_us_county_" + year))
    shp = gpd.GeoDataFrame.from_file('US_county_' + year + '.shp')
    
    if year == '2010':
        shp = fix_2010(shp)
    
    shp['Year'] = year
    shp['area_base'] = shp.area
    

    ## intersecting
    temp = gpd.overlay(shp, shp_end, how = 'intersection')
    
    ## computing weights 
    temp['area'] = temp.area
    temp['weight'] = temp['area'] / temp['area_base']
    
    ## keeping only relevant variables
    temp = temp[['Year', 'NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM','ICPSRST', 'ICPSRCTY', 'area_base',
                      'cz', 'area', 'weight']]
    
    ## renormalizing weights
    reweight = temp.groupby(['NHGISCTY', 'NHGISST'])['weight'].sum().reset_index()
    reweight['new_weight'] = reweight['weight']
    reweight = reweight.drop('weight', axis = 1)
    
    temp = temp.merge(reweight, left_on = ['NHGISCTY', 'NHGISST'], right_on = ['NHGISCTY', 'NHGISST'])
    temp['weight'] = temp['weight'] / temp['new_weight']
    
    temp = temp.drop('new_weight', axis =1)

    ## making an indicator if the state is in the union
    states_year = states[states[year] ==1]['State']
    temp['US_STATE'] = 0
    temp.loc[temp['STATENAM'].isin(states_year.apply(str.strip)), 'US_STATE'] = 1

    ## appending
    master_df = master_df.append(temp)
    print(year, time.time() - start) 


## saving output
os.chdir(path)
master_df.to_csv('cz_crosswalk.csv', index= False)

#--- Uncomment to auto-open ---
# os.system('cz_crosswalk.csv')
