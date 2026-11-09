"""Build the list of towns, with their populations and locations, used by the population-based weights.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", working paper, 2026. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/towns.py
    python Code/towns.py --inputs /path/to/Inputs --shapefiles /path/to/Shapefiles

The town populations and the USGS GNIS place names must sit in the Inputs folder, as described in
Inputs/HowToAcquireInputs.txt; the NHGIS 2010 county map in the Shapefiles folder. The output is
written to Intermediate/towns.gpkg.

What the script does:
  1. Read the town populations of each census year from the US Historical City Populations list
     (Steiner and Heppler), which covers places that passed 2,500 people. Entries that come only from
     the Populstat compilation are left out, since they can count people already in incorporated
     places. A town's first location is the Census gazetteer coordinate, or the list's geocoded one.
     Towns that do not lie in their own state are dropped.
  2. Move each town to its USGS GNIS "Populated Place" point, which marks the traditional town center:
     same state, same name after simple cleaning, the nearest such point within 25 kilometers.
  3. Correct the list where the census record is clear (see fix_towns below).
"""
import argparse
import glob
import os
import re

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from crosswalk_county import find_shapefile

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)
MAX_MOVE_M = 25000          # a town moves to a GNIS point at most 25 km away
NHGIS_ALBERS = 'ESRI:102003'   # the projection of the NHGIS maps: USA Contiguous Albers Equal Area (NAD83)

# State FIPS codes by postal abbreviation; IT is Indian Territory, today's Oklahoma.
FIPS = {'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11',
        'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21',
        'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29', 'MT': '30',
        'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
        'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49',
        'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56', 'IT': '40'}


def read_town_list(src, county2010_shp):
    """Towns with their populations by census year (columns pop1790 ... pop2010) and a first location."""
    d = pd.read_csv(src, low_memory=False)
    d = d[d['Population Source'] != 'Jan Lahmeyer'].copy()
    for c in ['LAT', 'LON', 'LAT_BING', 'LON_BING']:
        d[c] = pd.to_numeric(d[c], errors='coerce')                   # a few malformed entries become missing
        d.loc[d[c] == 0, c] = float('nan')                            # 0 is not a coordinate in the US
    census_coords = d['LAT'].notna() & d['LON'].notna()
    d['lat'] = d['LAT'].where(census_coords, d['LAT_BING'])
    d['lon'] = d['LON'].where(census_coords, d['LON_BING'])
    d['coord_source'] = census_coords.map({True: 'census', False: 'geocoded'})
    years = [c for c in d.columns if c.isdigit()]
    for y in years:
        d[y] = pd.to_numeric(d[y], errors='coerce').fillna(0)
    d = d[d['lat'].notna() & d['lon'].notna()]

    towns = gpd.GeoDataFrame(d[['ID', 'City', 'ST', 'STPLFIPS_2010', 'coord_source'] + years],
                             geometry=gpd.points_from_xy(d['lon'], d['lat']), crs=4326).to_crs(NHGIS_ALBERS)
    towns.columns = [f'pop{c}' if c in years else c for c in towns.columns]

    # The state each point lies in (a point just offshore: the nearest county within 10 km).
    counties = gpd.read_file(county2010_shp, columns=['STATEFP10', 'GEOID10']).to_crs(NHGIS_ALBERS)
    j = gpd.sjoin(towns, counties, how='left', predicate='within')
    j = j[~j.index.duplicated()]
    offshore = j['GEOID10'].isna()
    near = gpd.sjoin_nearest(towns[offshore.values], counties, how='left', max_distance=10000)
    near = near[~near.index.duplicated()]
    j.loc[near.index, ['STATEFP10', 'GEOID10']] = near[['STATEFP10', 'GEOID10']].values
    towns['in_state'] = j['STATEFP10'].values == towns['ST'].map(FIPS).values
    towns['GEOID10_point'] = j['GEOID10'].values
    print(f'town list: {len(towns)} towns with coordinates; {int((~towns["in_state"]).sum())} outside their own state dropped')
    return towns[towns['in_state']].reset_index(drop=True)


def clean(s):
    """A place name in simple form: lower case, "saint" -> "st", punctuation removed."""
    s = s.lower().replace('saint ', 'st ').replace('sainte ', 'ste ').replace('&', 'and')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def move_to_gnis(towns, gnis_dir):
    """Move each town to its GNIS point. point_source records the outcome: gnis, unmatched or too far."""
    g = pd.concat([pd.read_csv(f, sep='|', dtype=str, encoding='utf-8-sig',
                               usecols=['feature_name', 'feature_class', 'state_numeric', 'prim_lat_dec', 'prim_long_dec'])
                   for f in glob.glob(f'{gnis_dir}/**/DomesticNames_*.txt', recursive=True)])
    g = g[g['feature_class'] == 'Populated Place'].copy()
    g['lat'], g['lon'] = pd.to_numeric(g['prim_lat_dec']), pd.to_numeric(g['prim_long_dec'])
    g = g[(g['lat'] != 0) & g['lat'].notna()]
    g['key'] = g['feature_name'].map(clean)
    places = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g['lon'], g['lat']), crs=4326).to_crs(NHGIS_ALBERS)
    by_name = {k: v for k, v in places.groupby(['state_numeric', 'key'])}

    # Same state and same name; a trailing " city" is dropped if there is no match with it. Among
    # several matches, the one nearest the town's current point; accepted within 25 km.
    new_points, source = [], []
    for _, r in towns.iterrows():
        st, name = FIPS.get(r['ST']), clean(r['City'])
        cands = by_name.get((st, name))
        if cands is None and name.endswith(' city'):
            cands = by_name.get((st, name[:-5]))
        if cands is None:
            new_points.append(r.geometry); source.append('unmatched')
            continue
        dist = cands.distance(r.geometry).values
        k = int(np.argmin(dist))
        if dist[k] <= MAX_MOVE_M:
            new_points.append(cands.geometry.values[k]); source.append('gnis')
        else:
            new_points.append(r.geometry); source.append('too far')
    towns['point_source'] = source
    towns = towns.set_geometry(gpd.GeoSeries(new_points, crs=towns.crs))
    print('GNIS points:', towns['point_source'].value_counts().to_dict())
    return towns


def fix_towns(t):
    """Corrections to the town list, each a census fact.

    1. Towns without a real location are dropped: unmatched towns whose point is shared by three or more
       towns (44 California places such as "Auburn & vicinity" all sat on one point in Madera County), and
       "Middle Fork, Am River", CA, 1850, whose point lies about 200 km from the American River.
    2. Baker, OR, repeats Baker City, OR (same populations 1890-1950) and is dropped.
    3. Towns listed under both IT and OK in 1900 (Ardmore, Chickasha, Coalgate, Durant): the OK entries are set to 0.
    4. "Berklely", VA, is Berkley (annexed by Norfolk in 1906); it gets its GNIS point (feature 1496801).
    5. Oak Ridge, TN, was founded in 1942; its 1940 entry is set to 0.
    6. New York City from 1900 on is listed as its five boroughs, at their GNIS points, with the census counts
       of the boroughs. In 1880 and 1890 the Bronx part of New York County (wards 23 and 24, annexed 1874) is
       its own town, 51,980 and 88,908 people, at Morrisania.
    7. Alexandria, VA, 1900 is not placed: the census counts it as Alexandria city, a unit the 1900 map does not
       show (the crosswalk gives that unit its own row).
    8. New Orleans suburbs counted in Jefferson Parish (the NHGIS maps draw Orleans at its 2010 extent) are not
       placed: "Lafayette, LA" 1840-1850 and Jefferson City ("Jefferson, LA") 1860. The crosswalk moves their
       share of Jefferson Parish to Orleans.
    9. Broomfield, CO, 1990-2000 spanned four counties (Broomfield County was formed in 2001); it is split into
       four towns by the shares of its 2010 population in each county part (Adams 50.0%, Boulder 42.0%,
       Jefferson 5.5%, Weld 2.5%), each at an interior point of that part, also in 2010.
    10. Los Alamos, NM, a census-designated place never incorporated, is added: census counts 1950-2010 at its
        GNIS point (feature 901357).
    11. Pawtucket, MA (1860) and Fall River, RI (1860), the towns that changed state in 1862, get points inside
        the land that moved. Pawtucket, MA, 1850 (3,753 people, missing from the list) is added.
    12. Buena Vista, VA, is its own city from 1900 (2,388 people) but in the list only from 1910; its 1900
        count is added."""
    popcols = [c for c in t.columns if c.startswith('pop') and c[3:].isdigit()]
    n_in = len(t)

    def is_town(city, st):
        return (t['City'] == city) & (t['ST'] == st)

    def new_towns(rows, crs):
        """New towns (dicts with populations, City, ST and a longitude-latitude Point) in the list's projection."""
        return gpd.GeoDataFrame(rows, geometry='geometry', crs=4326).to_crs(crs)

    def blank():
        return {c: 0.0 for c in popcols}

    # 1. towns without a real location
    key = t.geometry.apply(lambda p: (round(p.x), round(p.y)))
    t = t[~((t['point_source'] == 'unmatched') & (key.map(key.value_counts()) >= 3))]
    t = t[~is_town('Middle Fork, Am River', 'CA')]

    # 2. Baker, OR (unmatched) repeats Baker City, OR
    t = t[~(is_town('Baker', 'OR') & (t['point_source'] == 'unmatched'))]

    # 3. Indian Territory towns also listed under Oklahoma in 1900
    in_it = set(t.loc[(t['ST'] == 'IT') & (t['pop1900'] > 0), 'City'])
    t.loc[(t['ST'] == 'OK') & t['City'].isin(in_it), 'pop1900'] = 0

    # 4. Berkley, VA
    b = is_town('Berklely', 'VA')
    t.loc[b, 'City'] = 'Berkley'
    t.loc[b, 'geometry'] = gpd.GeoSeries([Point(-76.2838292, 36.8318147)], crs=4326).to_crs(t.crs).iloc[0]
    t.loc[b, 'point_source'] = 'gnis'

    # 5. Oak Ridge, TN, before its founding
    t.loc[is_town('Oak Ridge', 'TN'), 'pop1940'] = 0

    # 6. New York City as five boroughs from 1900; the Bronx annexed district in 1880 and 1890
    nyc = is_town('New York City', 'NY')
    for c in popcols:
        if int(c[3:]) >= 1900:
            t.loc[nyc, c] = 0
    boroughs = {   # census counts; Manhattan and the Bronx in 1900 and 1910 are borough counts within New York County
        'Manhattan': {1900: 1850093, 1910: 2331542, 1920: 2284103, 1930: 1867312, 1940: 1889924, 1950: 1960101,
                      1960: 1698281, 1970: 1539233, 1980: 1428285, 1990: 1487536, 2000: 1537195, 2010: 1585873},
        'Bronx': {1900: 200507, 1910: 430980, 1920: 732016, 1930: 1265258, 1940: 1394711, 1950: 1451277,
                  1960: 1424815, 1970: 1471701, 1980: 1168972, 1990: 1203789, 2000: 1332650, 2010: 1385108},
        'Brooklyn': {1900: 1166582, 1910: 1634351, 1920: 2018356, 1930: 2560401, 1940: 2698285, 1950: 2738175,
                     1960: 2627319, 1970: 2602012, 1980: 2230936, 1990: 2300664, 2000: 2465326, 2010: 2504700},
        'Queens': {1900: 152999, 1910: 284041, 1920: 469042, 1930: 1079129, 1940: 1297634, 1950: 1550849,
                   1960: 1809578, 1970: 1986473, 1980: 1891325, 1990: 1951598, 2000: 2229379, 2010: 2230722},
        'Staten Island': {1900: 67021, 1910: 85969, 1920: 116531, 1930: 158346, 1940: 174441, 1950: 191555,
                          1960: 221991, 1970: 295443, 1980: 352121, 1990: 378977, 2000: 443728, 2010: 468730},
    }
    gnis_points = {'Manhattan': (-73.9662495, 40.7834345), 'Bronx': (-73.8662464, 40.8501002),
                   'Brooklyn': (-73.9495823, 40.6501038), 'Queens': (-73.7976337, 40.7498243),
                   'Staten Island': (-74.1495875, 40.5834379)}
    rows = []
    for name, pops in boroughs.items():
        r = blank()
        r.update({f'pop{y}': float(v) for y, v in pops.items()})
        r.update(City=f'{name} (borough)', ST='NY', point_source='gnis', geometry=Point(*gnis_points[name]))
        rows.append(r)
    r = blank()
    r.update(pop1880=51980.0, pop1890=88908.0, City='Bronx (annexed district)', ST='NY', point_source='gnis',
             geometry=Point(-73.9065253, 40.8292672))            # Morrisania (GNIS 957700), west of the Bronx River
    rows.append(r)
    for y, v in {1880: 51980, 1890: 88908}.items():
        t.loc[nyc, f'pop{y}'] -= v
    added = new_towns(rows, t.crs)
    t = gpd.GeoDataFrame(pd.concat([t, added], ignore_index=True), geometry='geometry', crs=added.crs)

    # 7. Alexandria, VA, 1900: counted in a unit the map does not show
    t.loc[is_town('Alexandria', 'VA'), 'pop1900'] = 0

    # 8. New Orleans suburbs counted in Jefferson Parish
    t.loc[is_town('Lafayette', 'LA'), ['pop1840', 'pop1850']] = 0
    t.loc[is_town('Jefferson', 'LA'), 'pop1860'] = 0

    # 9. Broomfield, CO, by county part, 1990-2010 (shares from 2010 tracts)
    bf = is_town('Broomfield', 'CO')
    base = t.loc[bf].iloc[0]
    parts = {'Adams': (0.500, -105.034232, 39.957406), 'Boulder': (0.420, -105.064369, 39.945142),
             'Jefferson': (0.055, -105.080989, 39.907811), 'Weld': (0.025, -104.978523, 40.021543)}
    rows = []
    for name, (share, lon, lat) in parts.items():
        r = blank()
        r.update(pop1990=base['pop1990'] * share, pop2000=base['pop2000'] * share, pop2010=base['pop2010'] * share,
                 City=f'Broomfield ({name} part)', ST='CO', point_source='gnis', geometry=Point(lon, lat))
        rows.append(r)
    t.loc[bf, ['pop1990', 'pop2000', 'pop2010']] = 0
    t = gpd.GeoDataFrame(pd.concat([t, new_towns(rows, t.crs)], ignore_index=True), geometry='geometry', crs=t.crs)

    # 10. Los Alamos, NM
    r = blank()
    r.update(pop1950=9934.0, pop1960=12584.0, pop1970=11310.0, pop1980=11039.0, pop1990=11455.0, pop2000=11909.0,
             pop2010=12019.0, City='Los Alamos', ST='NM', point_source='gnis', geometry=Point(-106.3069722, 35.8880796))
    t = gpd.GeoDataFrame(pd.concat([t, new_towns([r], t.crs)], ignore_index=True), geometry='geometry', crs=t.crs)

    # 11. towns that changed state in 1862
    for (city, st), (lon, lat) in {('Pawtucket', 'MA'): (-71.370, 41.876), ('Fall River', 'RI'): (-71.16, 41.68)}.items():
        t.loc[is_town(city, st), 'geometry'] = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(t.crs).iloc[0]
    t.loc[is_town('Pawtucket', 'MA'), 'pop1850'] = 3753

    # 12. Buena Vista, VA, 1900
    t.loc[is_town('Buena Vista', 'VA'), 'pop1900'] = 2388

    print(f'corrections: {n_in} towns -> {len(t)}')
    return t


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inputs', default=os.path.join(ROOT, 'Inputs'))
    parser.add_argument('--shapefiles', default=os.path.join(ROOT, 'Shapefiles'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Intermediate'))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    towns = read_town_list(os.path.join(args.inputs, 'city_populations', '1790-2010_MASTER.csv'),
                           find_shapefile(args.shapefiles, 'US_county_2010.shp'))
    towns = move_to_gnis(towns, os.path.join(args.inputs, 'gnis'))
    towns = fix_towns(towns)
    out = os.path.join(args.out, 'towns.gpkg')
    towns.to_file(out, driver='GPKG')
    print('saved', out)


if __name__ == '__main__':
    main()
