# EGLP_Crosswalk: Crosswalks

We provide a series of three crosswalks: for each year y in 1790, 1800, 1810, ..., 2010, we map counties in the year y to 1990 counties, 2010 counties, and 1990 commuting zones<sup>1</sup>.  Obviously we do not map 1990 counties to 1990 counties, nor do we map 2010 counties to 2010 counties.

For each crosswalk, we identify counties by two sets of codes: NHGIS codes, and ICPSR codes, when available. NHGIS codes are a strict superset of FIPS codes, in the sense that when both NHGIS and FIPS codes exist, the NHGIS code is equal to the FIPS code with an additional zero. ICPSR codes are not always available: in particular, in 2010 the county files do not contain ICPSR codes. 

For simplicity, we also provide state (or territory) names, along with county names. We also provide an indicator if the (historical) geographic region is part of a US state. 

We provide the areas of relevant regions, in square meters. The 'area_base' column denotes the total area of the historic county, and 'area' provides the area of the intersection of the historic county and the modern county or commuting zone. Areas less than 10 square meters are suppressed. 

For an example of how to use the crosswalk, see the Example folder.






<sup>1</sup> We use the 1990 commuting zone shapefile provided by The Health Inequality Project here: https://healthinequality.org/data/
