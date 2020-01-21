# EGLP_Crosswalk: Crosswalk Example

We provide a brief example of how to use the crosswalk. In particular, we map 1900 population data downloaded from NHGIS to 2010 counties. 

The population data inputs are downloaded directly from NHGIS, and includes 'nhgis0014_ds31_1900_county.csv', a csv file of counties and populations (in column AYM001) and 'nhgis0014_ds31_1900_county_codebook.txt', containing the codebook for the aforementioned csv. The  crosswalk is 'county_crosswalk_endyr_2010.csv'.

In the python file, we demonstrate how to use the crosswalk. The exercise proceeds in three steps: (1) read in the data and the crosswalk, (2) merge the crosswalk and the data, and (3) scale the population figures by the crosswalk weights, and collapse on the 2010 identifiers.

In step (1), running from lines 1 to 21, we set some paths and read in the data. Running this code will of course require one to change the path, as well as possibly the folder structure. we keep only the relevant year in the crosswalk, that is to say, 1900.

In step (2), running from lines 23 to 32, we generate a county identifier for the population data and for the crosswalk. we use the equivalent of the FIPS code, where we combine the NHGIS State and County codes for the crosswalk, and combine the STATEA and COUNTYA codes in the population data. We then drop columns in the population data that will not be merged to the crosswalk - this consists of several territories with codes that are not in the NHGIS concordance and typically do not have data. On line 31, as a check, we print the total population. Then we perform the merge. 

Finally, in step (3), running from lines 34 to the end, we rescale the population data and collapse on the later period identifiers. In principle, it is sufficient to collapse on NHGISST_2010 and NHGISCTY_2010, but it is nice to have the state and county names in the merged data, so we collapse on these as well. Then, we save the output and print the total population spread across 2010 counties, and verify that it is the same.