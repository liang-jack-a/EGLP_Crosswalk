# EGLP_Crosswalk: Crosswalk Example

We provide a brief example of how to use the crosswalk. In particular, we map 1900 population data downloaded from NHGIS to 2010 counties. 

The population data inputs are downloaded directly from NHGIS, and includes 'nhgis0014_ds31_1900_county.csv', a csv file of counties and populations (in column AYM001) and 'nhgis0014_ds31_1900_county_codebook.txt', containing the codebook for the aforementioned csv. The  crosswalk is 'county_crosswalk_endyr_2010.csv'.

In the python file, I demonstrate how to use the crosswalk. The exercise proceeds in three steps: (1) read in the data and the crosswalk, (2) merge the crosswalk and the data, and (3) scale the population figures by the crosswalk weights, and collapse on the 2010 identifiers.

In step (1), running from lines 1 to 21, I set some paths and read in the data. Running this code will of course require one to change the path, as well as possibly the folder structure. I keep only the relevant year in the crosswalk, that is to say, 1900.

In step (2), running from lines 24 to 