* Map 1900 county population from NHGIS to 2010 counties with the EGLP crosswalk.
* Eckert, Gvirtz, Liang, Peters, NBER WP 26770, www.fpeckert.me/eglp
*
* Run from the repository root:   do Example/crosswalk_example.do
* Reads  Crosswalks/Stata/county_crosswalk_endyr_2010.dta.zip
*        Example/Data/nhgis0014_ds31_1900_county.csv
* Writes Example/example_output_stata.csv

clear all

* 1. The crosswalk: unzip it once, keep the rows for the year of the data.
local root = c(pwd)
quietly cd "Crosswalks/Stata"
capture confirm file "county_crosswalk_endyr_2010.dta"
if _rc unzipfile "county_crosswalk_endyr_2010.dta.zip"
quietly cd "`root'"
use if Year == 1900 using "Crosswalks/Stata/county_crosswalk_endyr_2010.dta", clear
tempfile cw
save `cw'

* 2. The data: NHGIS county population in 1900. Every NHGIS extract has a GISJOIN column.
import delimited "Example/Data/nhgis0014_ds31_1900_county.csv", case(preserve) stringcols(_all) encoding(latin1) clear
destring AYM001, replace
summarize AYM001, meanonly
display "1900 population before mapping: " %15.0fc r(sum)

* 3. Merge on GISJOIN. Each 1900 county gets one row per 2010 county it overlaps.
*    A few territories in the population file are not on the NHGIS 1900 map; they drop out here.
merge 1:m GISJOIN using `cw', keep(match) nogenerate

* 4. Split each county's population by the weights and add up within 2010 counties.
generate double population = AYM001 * weight
collapse (sum) population, by(FIPS_2010 STATENAM_2010 NHGISNAM_2010)
summarize population, meanonly
display "1900 population after mapping to 2010 counties: " %15.0fc r(sum)

export delimited using "Example/example_output_stata.csv", replace
