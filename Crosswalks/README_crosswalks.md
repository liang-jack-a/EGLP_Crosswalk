# EGLP_Crosswalk: Crosswalks

There are three crosswalks. For each census year from 1790 to 2010, they map that year's counties to 1990 counties (`county_crosswalk_endyr_1990.csv`), to 2010 counties (`county_crosswalk_endyr_2010.csv`), and to 1990 commuting zones (`cz_crosswalk.csv`)<sup>1</sup>. The 1990 county file has no rows for 1990 and the 2010 county file has no rows for 2010, since those maps would map to themselves.

All years are stacked in one file. Keep only the rows of the year of your data (column `Year`).

## Identifiers

Each row links one historical unit to one reference unit.

Ready-made merge keys:

- `GISJOIN`: the NHGIS identifier of the historical unit, e.g. `G0100010` for Autauga County, Alabama. Every NHGIS data extract and shapefile has this column, so NHGIS data merge directly.
- `FIPS_1990` and `FIPS_2010` (county crosswalks only): the five-digit FIPS code of the reference county, as text with leading zeros, e.g. `01001`. Most modern county data use this code.
- `GISJOIN_1990` and `GISJOIN_2010` (county crosswalks only): the NHGIS identifier of the reference county.

The underlying codes:

- `NHGISST`, `NHGISCTY`: NHGIS state and county codes of the historical unit. For counties that have a FIPS code, the NHGIS code is the FIPS code with a zero appended: FIPS state 51 is NHGIS state 510, and FIPS county 650 is NHGIS county 6500. Counties that no longer exist have NHGIS codes but no FIPS codes. In the rows for 2010, `NHGISCTY` is the three-digit FIPS county code, as in the NHGIS 2010 map.
- `ICPSRST`, `ICPSRCTY`: ICPSR codes, where they exist. Not every unit has one.
- The reference counties have the same codes with a suffix for the reference year. In the 2010 file, `NHGISCTY_2010` is the three-digit FIPS county code (650), not the four-digit NHGIS code (6500), and `ICPSRST_2010` and `ICPSRCTY_2010` are empty, because ICPSR codes do not exist for 2010 counties.
- `cz` (commuting zone file): the 1990 commuting zone code.

The files also give state and county names (`STATENAM`, `NHGISNAM`). `US_STATE` is 1 if the historical unit lies in a state that was part of the Union in that year, and 0 if it lies in a territory. The District of Columbia always has `US_STATE` = 0.

## Stata files

`Stata/` holds the same three crosswalks as Stata files, zipped to keep the repository small. `unzipfile` unpacks into Stata's current folder, so change to that folder first: `cd "Crosswalks/Stata"`, then `unzipfile "county_crosswalk_endyr_2010.dta.zip", replace`. Every variable has a label. The merge keys are text; the NHGIS and ICPSR codes are numbers.

## Areas and weights

`area_base` is the area of the historical county and `area` is the area of the piece that lies in the reference unit, both in square meters. Pieces of 10 square meters or less are dropped. `weight` is the share of the historical county's area within the reference map that lies in the reference unit: the areas of the pieces kept, divided by their sum, so that the weights of each historical county sum to one. It equals `area / area_base` when the whole county lies on the reference map. Where it does not (for example, where two maps draw a coastline differently, or a slice of the county is cut off by a dropped sliver), the weights are scaled up to sum to one; in the 2010 file the difference is below 1% of the county's area for 98% of county-decades.

To move a stock variable such as population to the reference map, multiply each historical county's value by its weights and sum within reference units. For averages, use `area` to compute the share of each reference unit's area that comes from each historical county. See the Example folder for complete scripts in Python and Stata.

<sup>1</sup> We use the 1990 commuting zone shapefile of the Health Inequality Project: https://healthinequality.org/data/
