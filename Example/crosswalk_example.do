* Map 1900 county population from NHGIS to 2010 counties with the EGLP crosswalk.
* Eckert, Gvirtz, Liang, Peters, NBER WP 26770, www.fpeckert.me/eglp
*
* Run from the repository root:   do Example/crosswalk_example.do
* Reads  Crosswalks/Stata/county_crosswalk_endyr_2010.dta.zip
*        Example/Data/nhgis0014_ds31_1900_county.csv
* Writes Example/example_output_stata.csv

clear all

* 1. The crosswalk: unzip it (unzipfile unpacks into the current folder, hence the cd),
*    then keep the rows for the year of the data.
local root = c(pwd)
quietly cd "Crosswalks/Stata"
unzipfile "county_crosswalk_endyr_2010.dta.zip", replace
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
*    Report the units that do not match before dropping them: they are not on the NHGIS 1900 map
*    (here 69 units, 11 of them with population data: 16,024 people).
merge 1:m GISJOIN using `cw', keep(master match)
quietly count if _merge == 1
local n_units = r(N)
summarize AYM001 if _merge == 1, meanonly
display "not on the 1900 map: `n_units' units, " r(N) " of them with population data, " %12.0fc r(sum) " people"
keep if _merge == 3
drop _merge

* 4. Split each county's population by the weights and add up within 2010 counties.
generate double population = AYM001 * weight
* Note: collapse (sum) counts missing values as zero, so a 2010 county that only overlaps 1900 units
* without data gets 0. To keep such counties missing, add (count) n = population to the collapse and
* then: replace population = . if n == 0
collapse (sum) population, by(FIPS_2010 STATENAM_2010 NHGISNAM_2010)
summarize population, meanonly
display "1900 population after mapping to 2010 counties: " %15.0fc r(sum)

export delimited using "Example/example_output_stata.csv", replace
