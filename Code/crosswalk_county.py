import pandas as pd
import geopandas as gpd
import os
import time

path = '/Users/jackliang/Dropbox/Current/EGP_Liang/'

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

end_year = '2010'

## reading the end year
## if you want to use a different end year, change appropriate strings
## and variable names
os.chdir(path + '/Shapefiles/nhgis0010_shapefile_tl2000_us_county_' + end_year)
shp_end = gpd.GeoDataFrame.from_file('US_county_' + end_year + '.shp')

if end_year == '2010':
    shp_end = fix_2010(shp_end)

    
    
cols = shp_end.columns
new_cols_end = []
for col in cols:
    if col != 'geometry':
        new_cols_end = new_cols_end + [col + '_' + end_year]
    else:
        new_cols_end = new_cols_end + [col]

shp_end.columns = new_cols_end

## looping through other years
other_years = ['1790', '1800', '1810', '1820', '1830', '1840', 
             '1850', '1860', '1870', '1880', '1890', '1900', '1910',
             '1920', '1930', '1940', '1950', '1960', '1970',
             '1980', '1990', '2000', '2010']
other_years.remove(end_year)

for year in other_years:
    
    start = time.time() ## for testing purposes
    
    ## reading in shapefiles
    os.chdir(path + '/Shapefiles/nhgis0010_shapefile_tl2000_us_county_' + year)
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
    temp = temp[['Year', 'NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM','ICPSRST', 'ICPSRCTY',
                 'area_base', 'NHGISST_' + end_year, 'NHGISCTY_' + end_year, 'STATENAM_' + end_year, 'NHGISNAM_' + end_year, 'ICPSRST_' + end_year, 'ICPSRCTY_' + end_year,
                 'area', 'weight']]

    temp = temp[temp['area'] > 10]
    
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
master_df.to_csv('county_crosswalk_endyr_' + end_year + '.csv', index= False)