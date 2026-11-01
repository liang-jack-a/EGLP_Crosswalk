# EGLP_Crosswalk

Code and crosswalks for Eckert, Gvirtz, Liang and Peters, "A Method to Construct Geographical Crosswalks with an Application to US Counties since 1790", NBER Working Paper 26770 (2020). The paper and the shapefiles are at [www.fpeckert.me/eglp](https://www.fpeckert.me/eglp).

## What is here

| Folder | Contents |
|---|---|
| `Crosswalks/` | The three crosswalks: historical counties (1790 to 2010) to 1990 counties, to 2010 counties, and to 1990 commuting zones. See `Crosswalks/README_crosswalks.md`. |
| `Code/` | The code that builds the three crosswalks, a general script that builds a crosswalk between any two maps, and a script that checks a rebuilt crosswalk against the posted one. See `Code/README_crosswalk_generation.md`. |
| `Example/` | An example that maps 1900 county population to 2010 counties. See `Example/README_example.md`. |
| `Shapefiles/` | Where the shapefiles go. They are not in the repository; `Shapefiles/HowToAcquireShapeFiles.txt` says where to get them. |

## Running the code

Install the packages with `pip install -r requirements.txt` (Python 3.10 or later). Put the shapefiles in `Shapefiles/`, then run from the repository root:

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
