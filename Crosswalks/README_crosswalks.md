# EGLP_Crosswalk: Crosswalks

There are three crosswalks. For each census year from 1790 to 2010, they map that year's counties to 1990 counties (`county_crosswalk_endyr_1990.csv`), to 2010 counties (`county_crosswalk_endyr_2010.csv`), and to 1990 commuting zones (`cz_crosswalk.csv`)<sup>1</sup>. The 1990 county file has no rows for 1990 and the 2010 county file has no rows for 2010, since those maps would map to themselves.

All years are stacked in one file. Keep only the rows of the year of your data (column `Year`).

## Identifiers

Historical counties are identified by NHGIS codes (`NHGISST`, `NHGISCTY`) and, where they exist, ICPSR codes (`ICPSRST`, `ICPSRCTY`). For counties that have a FIPS code, the NHGIS code is the FIPS code with a zero appended: FIPS state 51 is NHGIS state 510, and FIPS county 650 is NHGIS county 6500. Counties that no longer exist have NHGIS codes but no FIPS codes.

The reference counties are identified the same way, with a suffix for the reference year, with two exceptions in the 2010 file:

- `NHGISCTY_2010` is the three-digit FIPS county code (650), not the four-digit NHGIS code (6500). `NHGISST_2010` is the NHGIS state code (510).
- `ICPSRST_2010` and `ICPSRCTY_2010` are empty, because ICPSR codes do not exist for 2010 counties.

The files also give state and county names (`STATENAM`, `NHGISNAM`). `US_STATE` is 1 if the historical county lies in a state that was part of the Union in that year, and 0 if it lies in a territory. The District of Columbia always has `US_STATE` = 0.

## Areas and weights

`area_base` is the area of the historical county and `area` is the area of the piece that lies in the reference unit, both in square meters. `weight` is the share of the historical county's area that lies in the reference unit; the weights of each historical county sum to one. Pieces of 10 square meters or less are dropped in all three files.

To move a stock variable such as population to the reference map, multiply each historical county's value by its weights and sum within reference units. For averages, use `area` to compute the share of each reference unit's area that comes from each historical county. See the Example folder.

<sup>1</sup> We use the 1990 commuting zone shapefile of the Health Inequality Project: https://healthinequality.org/data/
