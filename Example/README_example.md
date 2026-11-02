# EGLP_Crosswalk: Crosswalk Example

This example maps 1900 county population from NHGIS to 2010 counties. Run it with `python Example/crosswalk_example.py`.

The inputs are `Data/nhgis0014_ds31_1900_county.csv`, downloaded from NHGIS, with county population in the column `AYM001`; its codebook `Data/nhgis0014_ds31_1900_county_codebook.txt`; and the crosswalk `Crosswalks/county_crosswalk_endyr_2010.csv`.

The script works in three steps.

1. It reads the population data and the crosswalk, and keeps only the crosswalk rows for 1900.
2. It builds one county identifier in both files: the NHGIS state and county codes (`STATEA` and `COUNTYA` in the population data, `NHGISST` and `NHGISCTY` in the crosswalk). It drops a few territories in the population data whose codes are not on the NHGIS maps, prints the total population, and merges the two files.
3. It multiplies each 1900 county's population by its weights, sums within 2010 counties, saves the result as `example_output.csv`, and prints the total again. The two totals are the same (75,902,898), because the weights of each 1900 county sum to one.
