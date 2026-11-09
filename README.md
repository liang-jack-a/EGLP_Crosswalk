# EGLP_Crosswalk

Code and crosswalks for Eckert, Gvirtz, Liang and Peters, "A Method to Construct Geographical Crosswalks with an Application to US Counties since 1790", working paper, November 2026. An earlier version appeared as NBER Working Paper 26770 (2020). The paper and the 1990 commuting zone shapefile are at [www.fpeckert.me/eglp](https://www.fpeckert.me/eglp).

This repository is the home of the crosswalk files and code; the website links here.

## Using a crosswalk in four steps

1. Pick the file for the map you want your data on: 1990 counties, 2010 counties, or 1990 commuting zones. Keep the rows whose `Year` is the census year of your data (or the nearest census year).
2. Merge your data onto the crosswalk. For data from NHGIS, merge on `GISJOIN`, which every NHGIS extract and the crosswalk both have. Otherwise merge on the NHGIS state and county codes in the crosswalk, `NHGISST` and `NHGISCTY` (in the crosswalk's rows for 2010, `NHGISCTY` is the three-digit FIPS county code). Check which rows did not match: units that are not on that year's NHGIS map drop out.
3. Multiply each variable that is a count (population, payroll, farms) by `weight`, or by one of the other two weights described below.
4. Add up within the units of the new map: `FIPS_2010` or `FIPS_1990` (five-digit FIPS codes, as most modern data use them) or `cz`.

In Python:

```python
cw = pd.read_csv("Crosswalks/county_crosswalk_endyr_2010.csv", dtype={"GISJOIN": str, "FIPS_2010": str})
cw = cw[cw["Year"] == 1900]
df = data.merge(cw, on="GISJOIN")
df["population"] = df["population"] * df["weight"]
out = df.groupby("FIPS_2010", as_index=False)["population"].sum()
```

In Stata, with `mydata.dta` holding one row per 1900 county with `GISJOIN` and `population` (`unzipfile` unpacks into the current folder, hence the `cd`):

```stata
cd "Crosswalks/Stata"
unzipfile "county_crosswalk_endyr_2010.dta.zip", replace
cd "../.."
use if Year == 1900 using "Crosswalks/Stata/county_crosswalk_endyr_2010.dta", clear
merge m:1 GISJOIN using "mydata.dta", keep(match) nogenerate
generate double population_2010 = population * weight
collapse (sum) population_2010, by(FIPS_2010)
```

`Example/` has both versions as complete scripts that run.

## Three sets of weights

Each crosswalk file has three weights. Each sums to one for each historical county.

- `weight`: the share of the historical county's area in the reference unit (area-based weights).
- `weight_livable`: the share of its livable land: land that is not a natural water body, not above 3,500 meters and not steeper than 15 degrees.
- `weight_population`: the share of its people. The county's towns sit at their locations, and the rest of its people are spread as the rural population was spread at later censuses (paper, Section 3.3).

The livable-area and population-based weights cover the contiguous United States; they are empty for Alaska and Hawaii. The population-based weights suit population and variables distributed like population. For other variables, the livable-area weights are a more agnostic choice. To use them, replace `weight` with `weight_population` or `weight_livable` in step 3.

## What is here

| Folder | Contents |
|---|---|
| `Crosswalks/` | The three crosswalks: historical counties (1790 to 2010) to 1990 counties, to 2010 counties, and to 1990 commuting zones, as csv files and, in `Crosswalks/Stata/`, as zipped Stata files. See `Crosswalks/README_crosswalks.md`. |
| `Code/` | The code that builds the three crosswalks, a general script that builds a crosswalk between any two maps, and a script that checks a rebuilt crosswalk against the posted one. See `Code/README_crosswalk_generation.md`. |
| `Example/` | An example that maps 1900 county population to 2010 counties, in Python and in Stata. See `Example/README_example.md`. |
| `Shapefiles/` | Where the shapefiles go. They are not in the repository; `Shapefiles/HowToAcquireShapeFiles.txt` says where to get them. |
| `Inputs/` | Where the other inputs of the livable-area and population-based weights go: elevation, water bodies, dams, town populations, place names and county populations. They are not in the repository; `Inputs/HowToAcquireInputs.txt` says where to get them. |

## Running the code

Using the posted crosswalks needs only pandas (or Stata). Building them needs Python 3.12 or later and the packages in `requirements.txt`: `pip install -r requirements.txt`. Put the shapefiles in `Shapefiles/` (see `Shapefiles/HowToAcquireShapeFiles.txt`), then run from the repository root:

```
python Code/crosswalk_county.py --end-year 1990
python Code/crosswalk_county.py --end-year 2010
python Code/crosswalk_cz.py
```

Each script takes a few minutes. On 2026-11-01, with the versions in `requirements.txt`, the county scripts reproduced the posted county crosswalks: the same rows, with weights that differ by less than 4 parts in a billion.

The livable-area and population-based weights also need the files in `Inputs/` (see `Inputs/HowToAcquireInputs.txt`). Then run, after the scripts above:

```
python Code/livable_land.py
python Code/towns.py
python Code/crosswalk_county_population.py --end-year 1990
python Code/crosswalk_county_population.py --end-year 2010
python Code/crosswalk_cz_population.py
```

They add the columns `weight_livable` and `weight_population` to the three crosswalk files and leave the other columns as they are. See `Code/README_crosswalk_generation.md`.

## Changes in November 2026

- The scripts run on current versions of pandas and geopandas (`DataFrame.append` was removed in pandas 2.0) and take the shapefile and output folders as arguments.
- The commuting zone crosswalk now drops intersections of 10 square meters or less, as the county crosswalks and the paper do. This removed 375 slivers from the commuting zone file; no other weight changed by more than 3 parts in 100 million.
- The general script runs (it stopped with an error in the version on the website), measures areas in an equal-area projection, works when both maps use the same ID column name, and checks its inputs.
- The 2010 county crosswalk in this repository is now the same file as on the website (it had lost the leading zeros of the county codes and the two empty ICPSR columns).

## Changes in November 2026, second update

- Ready-made merge keys in all three crosswalks: `GISJOIN` for the historical unit (the identifier in every NHGIS extract) and, in the county crosswalks, `GISJOIN_1990`/`GISJOIN_2010` and `FIPS_1990`/`FIPS_2010` (five-digit FIPS codes) for the reference county. They are computed from the NHGIS codes in the file (`Code/merge_keys.py`) and match the GISJOIN codes of the NHGIS shapefiles for every year. No other value changed.
- Stata versions of the three crosswalks, with variable labels (`Crosswalks/Stata/`, made by `Code/make_stata_files.py`), and a Stata version of the example.
- The example merges on `GISJOIN` and sums by `FIPS_2010`. Its results are unchanged.

## Changes in November 2026, third update

- Two more weights in all three crosswalks: `weight_livable` (the share of the historical county's livable land) and `weight_population` (the share of its people), for the contiguous United States. They are built by `Code/livable_land.py`, `Code/towns.py`, `Code/crosswalk_county_population.py` and `Code/crosswalk_cz_population.py`. The columns that were already in the files did not change.
- New rows: Alexandria city, Virginia, 1900, which has a census count but no polygon on the 1900 map (all three crosswalks), and 52 pieces in the commuting zone file that only the new weights have, because they give each piece of land the commuting zone of its 1990 county. Their area-based `weight` is empty (Alexandria) or 0.

## Changes in November 2026, fourth update

- `weight_livable` is now the share of the historical county's livable land in every row. Before, it spread the county's census count over its livable land, so map units without a census count (229 county-years of 179 map units) got their share of grid cells instead. This changes `weight_livable` in 174 of these county-years in the 2010 county file, 106 in the 1990 county file and 94 in the commuting zone file. No other value changed by more than 1 in 100 million.
- `Crosswalks/README_crosswalks.md` lists the data corrections and the errors we know remain.
- The README and the scripts cite the November 2026 version of the paper.

## Changes in November 2026, fifth update

- The general script (`Code/crosswalk_generic.py`) works when an ID column is called `area`, `area_base` or `weight`. Before, the columns it adds overwrote such an ID column and it wrote wrong IDs and weights without an error. For other names its output is unchanged, byte for byte.
