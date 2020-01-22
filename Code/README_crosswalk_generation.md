# EGLP_Crosswalk: Code

We provide three sets of code that, in combination with shapefiles that can be found [here](http://fpeckert.me/eglp/), produce the crosswalks found in the Crosswalks folder. 

In order to run any of the code, one must use Python version 3.4 or later. Additionally, the packages [pandas](https://pandas.pydata.org/), [numpy](https://numpy.org/) and [geopandas](http://geopandas.org/) are all necessary. Additional packages including os and time (pre-installed in any python installation) are also useful.

The first two sets of code, 'crosswalk_county.py' and 'crosswalk_cz.py', generate crosswalks mapping historic counties to modern day counties and commuting zones, respectively. These crosswalks can be found in the Crosswalks folder.

Beyond what is described in the paper, these files perform some operations that should be noted. First, due to the 2010 shapefile being of a slightly different format (in terms of column names), we perform some modifications to the 2010 shapefile. This also involves using the file 'state_name_cw.csv' to map FIPS codes in 2010 states to state names.

Second, we loop through a large range of years and create, for each historic year, a crosswalk mapping the historic year to the modern year. This in principle creates several crosswalks which we stack on top of each other to create the master crosswalk. As demonstrated in the example, when using the crosswalk, it is necessary to specify only one origin year when performing the mapping, and thus keep only rows with that year.

Third, we create an indicator for each region that indicates if the region is, in the historical year, a US state. This involves the file 'states_union.csv'. 

Finally, for the commuting zone code, we find that the commuting zone shapefile has a different projection than the files downloaded from NHGIS, which follow the TIGER line concordance (which uses the NAD83 projection system). As such, in lines 41 to 50, we remedy this by re-projecting the commuting zone shapefile to NAD83.


The third code provides a way to use two generic shapefiles to create a crosswalk. For the code to be usable, one must first ensure that the two shapefiles are intersecting (as otherwise the crosswalk would clearly be empty), and use the same projection system. For an example of how to change the projection system of a shapefile in python, see the 'crosswalk_cz.py' file. 

To create the crosswalk, one must specify some variables. Primarily these are file paths and file names, however, two variables, origin_geoid and destination_geoid, are of critical importance. For each shapefile, it is necessary to have some unique identifier for each region. In the historic data, this role was filled by the NHGISST and NHGISCTY codes, and the cz column in the commuting zone shapefile. If multiple columns uniquely identify the geography, as in the case of historic counties, we suggest combining the two columns in an intuitive way, however, for an example where we keep the columns as is, see the 'crosswalk_county.py' file. 

The file generated will contain only three columns: the origin_geoid, the destination_geoid, and the weight. For an example of how to use such a crosswalk, see the Example folder. 