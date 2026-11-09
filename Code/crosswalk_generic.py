"""Build a crosswalk between any two maps of the same territory.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", NBER WP 26770. www.fpeckert.me/eglp

Fill in the values in ALL_CAPS below (see Appendix B of the paper), then run
    python crosswalk_generic.py

The output is a csv file with three columns: the ID of the reporting unit, the ID of the
reference unit, and the weight. The weight is the share of the reporting unit's area that lies
in the reference unit, so the weights of each reporting unit sum to one. Multiply a stock
variable (population, payroll) of each reporting unit by the weights and sum within reference
units to move the data to the reference map. When reading the output, read the ID columns
as text (e.g. pd.read_csv(..., dtype=str)) so that codes such as FIPS keep their leading zeros.
"""
import os

import geopandas as gpd

# ---------------------------------------------------------------------------
# Settings: replace the values in ALL_CAPS
# ---------------------------------------------------------------------------
reporting_path = 'PATH_REPORTING'     # folder that holds the reporting shapefile
reporting_fname = 'REPORTING_FNAME'   # e.g. 'US_county_1900.shp'
reporting_geoid = 'REPORTING_GEOID'   # column that identifies each reporting unit

reference_path = 'PATH_REFERENCE'     # folder that holds the reference shapefile
reference_fname = 'REFERENCE_FNAME'   # e.g. 'US_county_2010.shp'
reference_geoid = 'REFERENCE_GEOID'   # column that identifies each reference unit

output_path = 'OUTPUT_PATH'           # folder for the crosswalk
output_fname = 'OUTPUT_FNAME'         # e.g. 'crosswalk_1900_2010.csv'

# Optional settings
min_area = 0          # drop intersections of this area or less (in square meters when the
                      # area projection is in meters; the county crosswalks use 10)
area_crs = None       # projection used to measure areas. None: use the reporting map's own
                      # projection if it preserves areas, otherwise the equal-area EPSG:6933.
                      # For US maps, the NHGIS projection 'ESRI:102003' is a good choice.


def is_equal_area(crs):
    """True if the projection preserves areas (Albers, Lambert azimuthal, cylindrical equal-area...)."""
    try:
        return crs.is_projected and 'equal area' in crs.coordinate_operation.method_name.lower()
    except AttributeError:
        return False


def read_map(path, fname, geoid):
    """Read one map and keep only its ID column and its polygons, after checking both."""
    shp = gpd.read_file(os.path.join(path, fname))
    if geoid not in shp.columns:
        raise KeyError(f"{fname} has no column '{geoid}'. Its columns are: {list(shp.columns)}")
    if shp.crs is None:
        raise ValueError(f"{fname} has no coordinate system (.prj file). Set one with .set_crs() first.")
    shp = shp[[geoid, 'geometry']]
    if shp[geoid].duplicated().any():
        # several polygons share one ID (e.g. islands stored as separate rows): merge them
        shp = shp.dissolve(by=geoid, as_index=False)
    return shp


def main():
    # Step 1: read the two maps.
    shp_reporting = read_map(reporting_path, reporting_fname, reporting_geoid)
    shp_reference = read_map(reference_path, reference_fname, reference_geoid)

    # Step 2: put both maps in one projection. Areas are measured in it, so it should preserve
    # areas (an "equal-area" projection); otherwise the weights are distorted.
    crs = area_crs
    if crs is None:
        if is_equal_area(shp_reporting.crs):
            crs = shp_reporting.crs           # e.g. the NHGIS maps (USA Contiguous Albers Equal Area)
        else:
            crs = 'EPSG:6933'                 # worldwide equal-area projection
            print(f"Measuring areas in EPSG:6933 (equal-area), not in the reporting map's "
                  f"{shp_reporting.crs.name}. Set area_crs to choose another equal-area projection.")
    shp_reporting = shp_reporting.to_crs(crs)
    shp_reference = shp_reference.to_crs(crs)

    # The two ID columns may have the same name (e.g. GEOID in both maps): keep them apart.
    rep_id, ref_id = reporting_geoid, reference_geoid
    if rep_id == ref_id:
        rep_id, ref_id = rep_id + '_reporting', ref_id + '_reference'
        shp_reporting = shp_reporting.rename(columns={reporting_geoid: rep_id})
        shp_reference = shp_reference.rename(columns={reference_geoid: ref_id})

    # Step 3: the area of each reporting unit, measured before the overlay.
    shp_reporting['area_base'] = shp_reporting.area

    # Step 4: overlay the maps. Each row of the result is a piece that lies in exactly one
    # reporting unit and one reference unit.
    intersect = gpd.overlay(shp_reporting, shp_reference, how='intersection')
    if intersect.empty:
        raise ValueError("The two maps do not overlap. Check that they cover the same territory.")
    # Step 5: drop pieces of min_area or less (slivers where the two maps draw the same
    # boundary slightly differently).
    intersect['area'] = intersect.area
    intersect = intersect[intersect['area'] > min_area]

    # Step 6: the weight is the share of the reporting unit's area that lies in the piece.
    intersect['weight'] = intersect['area'] / intersect['area_base']

    # Step 7: rescale so that each reporting unit's weights sum to one. Without this, small gaps
    # where the two maps do not line up exactly would lose a little of each unit.
    intersect['weight'] = intersect['weight'] / intersect.groupby(rep_id)['weight'].transform('sum')

    # Step 8: save one row per piece: reporting ID, reference ID, weight.
    output = intersect[[rep_id, ref_id, 'weight']]
    output.to_csv(os.path.join(output_path, output_fname), index=False)
    print(f"saved {len(output)} rows to {os.path.join(output_path, output_fname)}")


if __name__ == '__main__':
    main()
