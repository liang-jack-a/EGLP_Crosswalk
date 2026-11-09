# EGLP_Crosswalk: Code

The code needs Python 3.12 or later and the packages in `requirements.txt` (pandas, numpy, geopandas and its dependencies; rasterio and scipy for the livable-area and population-based weights). Install them with `pip install -r requirements.txt`.

## The county and commuting zone crosswalks

`crosswalk_county.py` builds the crosswalk from historical counties to 1990 or 2010 counties. `crosswalk_cz.py` builds the crosswalk from historical counties to 1990 commuting zones. Run them from the repository root:

```
python Code/crosswalk_county.py --end-year 1990
python Code/crosswalk_county.py --end-year 2010
python Code/crosswalk_cz.py
```

By default they look for the shapefiles anywhere under `Shapefiles/`, by file name (see `Shapefiles/HowToAcquireShapeFiles.txt`) and write to `Crosswalks/`. Use `--shapefiles` and `--out` to point elsewhere.

For each census year from 1790 to 2010, the scripts intersect that year's county map with the reference map, compute the area of each piece, and divide it by the area of the historical county. They drop pieces of 10 square meters or less, which come from small mismatches between the maps rather than real boundary changes, and rescale the remaining weights so that the weights of each historical county sum to one. The crosswalks for all years are stacked in one file; keep only the rows of the year you need.

Beyond what the paper describes, the scripts do four things:

1. The 2010 shapefile uses different column names. The scripts rename them to the NHGIS names and use `state_name_cw.csv` to add state names. In the 2010 map, `NHGISST` is the NHGIS state code (the FIPS code with a zero appended), `NHGISCTY` is the three-digit FIPS county code, and the ICPSR codes are empty. Puerto Rico is dropped.
2. They add `US_STATE`, which is 1 if the historical county lies in a state that was part of the Union in that year. The years of accession are in `states_union.csv`. The District of Columbia is not a state and always gets 0.
3. The commuting zone shapefile is in longitude and latitude. `crosswalk_cz.py` projects it to the projection of the NHGIS maps (USA Contiguous Albers Equal Area, NAD83) before intersecting.
4. They add ready-made merge keys with `merge_keys.py`: `GISJOIN` for the historical unit and, in the county crosswalks, `GISJOIN_<year>` and the five-digit `FIPS_<year>` for the reference county. They are computed from the NHGIS codes and equal the GISJOIN codes of the NHGIS shapefiles.

`make_stata_files.py` writes the zipped Stata versions of the three crosswalks in `Crosswalks/Stata/`, with variable labels:

```
python Code/make_stata_files.py
```

`check_crosswalks.py` compares a rebuilt crosswalk with a posted one and reports any pairs and weights that differ:

```
python Code/crosswalk_county.py --end-year 2010 --out /tmp
python Code/check_crosswalks.py Crosswalks/county_crosswalk_endyr_2010.csv /tmp/county_crosswalk_endyr_2010.csv 2010
```

## The livable-area and population-based weights

Four scripts add two more weights to the three crosswalks, as the columns `weight_livable` and `weight_population`. They need the inputs listed in `Inputs/HowToAcquireInputs.txt` and write their own intermediate files to `Intermediate/`. Run them from the repository root, after the area-based crosswalks:

```
python Code/livable_land.py
python Code/towns.py
python Code/crosswalk_county_population.py --end-year 1990
python Code/crosswalk_county_population.py --end-year 2010
python Code/crosswalk_cz_population.py
```

- `livable_land.py` builds the map of livable land on a grid of 250 meter squares: land that is not a natural water body of 1 square kilometer or more, not above 3,500 meters and not steeper than 15 degrees. Reservoirs count as land.
- `towns.py` builds the list of towns, with their census populations from the US Historical City Populations list and their locations from USGS GNIS, and corrects it where the census record is clear.
- `crosswalk_county_population.py` and `crosswalk_cz_population.py` place each historical county's people on a grid of 500 meter cells and add up the people of each piece of the county, using `population_weights.py`. The towns sit at their locations. The rural population (everyone outside the towns) is spread evenly over livable land in 2010; going back one census at a time, each county's rural population is spread in proportion to the rural population of the same cells at the next census. Thin strips along county lines that hold no town get no people. The weights are the shares of the county's people (`weight_population`) and of its livable land (`weight_livable`) in each reference unit.

The scripts read each crosswalk file as text and add the two columns after `weight`, so every other column stays exactly as it was. The map of livable land covers the contiguous United States; the two columns are empty for Alaska and Hawaii. The data corrections are listed in `towns.py` and `population_weights.py`.

## A crosswalk between any two maps

`crosswalk_generic.py` builds a crosswalk between any two maps of the same territory. Fill in the values in capitals at the top of the file, as described in Appendix B of the paper:

- `PATH_REPORTING`, `REPORTING_FNAME`: the folder and file name of the map your data come in.
- `PATH_REFERENCE`, `REFERENCE_FNAME`: the folder and file name of the map you want the data on.
- `REPORTING_GEOID`, `REFERENCE_GEOID`: the column in each map that identifies its units. They may have the same name; the output then calls them `<name>_reporting` and `<name>_reference`, as it also does when one of them is called `weight`.
- `OUTPUT_PATH`, `OUTPUT_FNAME`: where to save the crosswalk.

Both maps need a coordinate system (a `.prj` file). The script projects both to one projection before measuring areas: the reporting map's own projection if it preserves areas (an equal-area projection, such as the NHGIS maps' Albers projection), otherwise the worldwide equal-area EPSG:6933. A projection that does not preserve areas, such as Web Mercator, would distort the weights. Set `area_crs` to choose another; for US maps the NHGIS projection `ESRI:102003` is a good choice, because it preserves areas. Set `min_area` to drop slivers, as the county crosswalks do with 10 square meters.

The output has three columns: the reporting ID, the reference ID, and the weight. Read the ID columns as text (`pd.read_csv(..., dtype=str)`) so that codes such as FIPS keep their leading zeros. The weight is the share of the reporting unit's area that lies in the reference unit. For an example of how to use a crosswalk, see the Example folder.

With the NHGIS 1900 and 2010 county maps, `GISJOIN` and `GEOID10` as IDs, `min_area = 10`, this script gives the same weights as the posted 2010 county crosswalk for 1900.
