# EGLP_Crosswalk: Crosswalk Example

This example maps 1900 county population from NHGIS to 2010 counties, in Python and in Stata. Run either one from the repository root:

```
python Example/crosswalk_example.py
```

```
do Example/crosswalk_example.do
```

The inputs are `Data/nhgis0014_ds31_1900_county.csv`, downloaded from NHGIS, with county population in the column `AYM001`; its codebook `Data/nhgis0014_ds31_1900_county_codebook.txt`; and the 2010 county crosswalk (`Crosswalks/county_crosswalk_endyr_2010.csv`, or for Stata `Crosswalks/Stata/county_crosswalk_endyr_2010.dta.zip`, which the do-file unzips).

Both scripts work in four steps.

1. Keep the crosswalk rows for 1900.
2. Merge the population data onto the crosswalk on `GISJOIN`, the identifier NHGIS puts in every extract. A few territories in the population file are not on the NHGIS 1900 map and drop out; the population total goes from 75,933,450 to 75,902,898, the NHGIS total in Table E.1 of the paper.
3. Multiply each 1900 county's population by its weights.
4. Add up within 2010 counties, identified by the five-digit FIPS code `FIPS_2010`. The total stays 75,902,898, because the weights of each 1900 county sum to one.

The results are in `example_output.csv` (Python) and `example_output_stata.csv` (Stata). They agree to within a billionth of a person.
