# EGLP_Crosswalk

Code and crosswalks for Eckert, Gvirtz, Liang and Peters, "A Method to Construct Geographical Crosswalks with an Application to US Counties since 1790", NBER Working Paper 26770 (2020). The paper and the shapefiles are at [www.fpeckert.me/eglp](https://www.fpeckert.me/eglp).

This repository is the home of the crosswalk files and code; the website links here.

## Using a crosswalk in four steps

1. Pick the file for the map you want your data on: 1990 counties, 2010 counties, or 1990 commuting zones. Keep the rows whose `Year` is the census year of your data (or the nearest census year).
2. Merge your data onto the crosswalk. Data from NHGIS carry a `GISJOIN` column, which the crosswalk has too. Otherwise merge on the NHGIS state and county codes, `NHGISST` and `NHGISCTY` (in NHGIS extracts they are called `STATEA` and `COUNTYA` and stored as text with leading zeros, e.g. `010` and `0010`; in the crosswalk's rows for 2010, `NHGISCTY` is the three-digit FIPS county code). Check which rows did not match: units that are not on that year's NHGIS map drop out.
3. Multiply each variable that is a count (population, payroll, farms) by `weight`.
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

## What is here

| Folder | Contents |
|---|---|
| `Crosswalks/` | The three crosswalks: historical counties (1790 to 2010) to 1990 counties, to 2010 counties, and to 1990 commuting zones, as csv files and, in `Crosswalks/Stata/`, as zipped Stata files. See `Crosswalks/README_crosswalks.md`. |
| `Code/` | The code that builds the three crosswalks, a general script that builds a crosswalk between any two maps, and a script that checks a rebuilt crosswalk against the posted one. See `Code/README_crosswalk_generation.md`. |
| `Example/` | An example that maps 1900 county population to 2010 counties, in Python and in Stata. See `Example/README_example.md`. |
| `Shapefiles/` | Where the shapefiles go. They are not in the repository; `Shapefiles/HowToAcquireShapeFiles.txt` says where to get them. |

## Running the code

Using the posted crosswalks needs only pandas (or Stata). Building them needs Python 3.12 or later and the packages in `requirements.txt`: `pip install -r requirements.txt`. Put the shapefiles in `Shapefiles/` (see `Shapefiles/HowToAcquireShapeFiles.txt`), then run from the repository root:

```
python Code/crosswalk_county.py --end-year 1990
python Code/crosswalk_county.py --end-year 2010
python Code/crosswalk_cz.py
```

Each script takes a few minutes. On 2026-11-01, with the versions in `requirements.txt`, the county scripts reproduced the posted county crosswalks: the same rows, with weights that differ by less than 4 parts in a billion.

## Changes in November 2026

- The scripts run on current versions of pandas and geopandas (`DataFrame.append` was removed in pandas 2.0) and take the shapefile and output folders as arguments.
- The commuting zone crosswalk now drops intersections of 10 square meters or less, as the county crosswalks and the paper do. This removed 375 slivers from the commuting zone file; no other weight changed by more than 3 parts in 100 million.
- The general script runs (it stopped with an error in the version on the website), measures areas in an equal-area projection, works when both maps use the same ID column name, and checks its inputs.
- The 2010 county crosswalk in this repository is now the same file as on the website (it had lost the leading zeros of the county codes and the two empty ICPSR columns).

## Changes in November 2026, second update

- Ready-made merge keys in all three crosswalks: `GISJOIN` for the historical unit (the identifier in every NHGIS extract) and, in the county crosswalks, `GISJOIN_1990`/`GISJOIN_2010` and `FIPS_1990`/`FIPS_2010` (five-digit FIPS codes) for the reference county. They are computed from the NHGIS codes in the file (`Code/merge_keys.py`) and match the GISJOIN codes of the NHGIS shapefiles for every year. No other value changed.
- Stata versions of the three crosswalks, with variable labels (`Crosswalks/Stata/`, made by `Code/make_stata_files.py`), and a Stata version of the example.
- The example merges on `GISJOIN` and sums by `FIPS_2010`. Its results are unchanged.
