"""Build the map of livable land used by the livable-area and population-based weights.

Eckert, Gvirtz, Liang, Peters, "A Method to Construct Geographical Crosswalks
with an Application to US Counties since 1790", NBER WP 26770. www.fpeckert.me/eglp

Usage (from the repository root):
    python Code/livable_land.py
    python Code/livable_land.py --inputs /path/to/Inputs

The elevation tiles, the water bodies and the dams must sit in the Inputs folder, as described
in Inputs/HowToAcquireInputs.txt. The output is written to Intermediate/livable_land.tif.

What the script does, for the contiguous United States:
  1. Elevation and slope. Mosaic the GMTED2010 elevation tiles and reproject them to a grid of
     250 by 250 meter squares in the projection of the NHGIS maps. Slope is computed from the
     elevation differences to the neighboring squares.
  2. Natural water bodies. Keep the lakes, intermittent and dry lakes, glaciers, swamps and marshes
     of at least 1 square kilometer in the National Atlas hydrography. Reservoirs count as land:
     a lake is a reservoir if a major dam at least 40 feet high lies within 3 kilometers and the
     dam's listed reservoir area is at least a quarter of the lake's area.
  3. Livable land. A square is not livable if it lies in a natural water body, above 3,500 meters,
     or on a slope of more than 15 degrees.
"""
import argparse
import glob
import os

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

CODE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE_DIR)

# The projection of the NHGIS maps: USA Contiguous Albers Equal Area (NAD83), in meters.
NHGIS_ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
CELL = 250.0                                                       # side of a square, in meters
XMIN, YMIN, XMAX, YMAX = -2_380_000, -1_450_000, 2_270_000, 1_580_000   # the contiguous US with a margin
LONLAT = (-126, 23, -65, 50.5)                                     # the same area in longitude and latitude
MAX_ELEVATION_M = 3500
MAX_SLOPE_DEG = 15
MIN_WATER_KM2 = 1


def elevation_and_slope(dem_dir, out_dir):
    """Elevation (meters) and slope (tenths of a degree) on the 250 meter grid.

    Writes elevation_m.tif and slope_deg10.tif. Squares outside the elevation data get -32768."""
    tiles = [rasterio.open(p) for p in sorted(glob.glob(os.path.join(dem_dir, '*_gmted_mea075.tif')))]
    mosaic, mosaic_transform = merge(tiles, bounds=LONLAT, nodata=-32768)

    # Reproject to the grid, averaging the neighboring tile cells (bilinear).
    width, height = int((XMAX - XMIN) / CELL), int((YMAX - YMIN) / CELL)
    transform = from_origin(XMIN, YMAX, CELL, CELL)
    elev = np.full((height, width), -32768, dtype=np.float32)
    reproject(mosaic[0].astype(np.float32), elev, src_transform=mosaic_transform, src_crs=tiles[0].crs,
              src_nodata=-32768, dst_transform=transform, dst_crs=NHGIS_ALBERS, dst_nodata=-32768,
              resampling=Resampling.bilinear)
    valid = elev > -1000

    # Slope in degrees: the rise over the run to the neighboring squares.
    dzdy, dzdx = np.gradient(np.where(valid, elev, np.nan), CELL)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    slope = np.where(np.isfinite(slope), slope, 0)

    profile = dict(driver='GTiff', height=height, width=width, count=1, crs=NHGIS_ALBERS, transform=transform,
                   compress='deflate', tiled=True)
    with rasterio.open(os.path.join(out_dir, 'elevation_m.tif'), 'w', dtype='int16', nodata=-32768, **profile) as f:
        f.write(np.where(valid, np.round(elev), -32768).astype(np.int16), 1)
    with rasterio.open(os.path.join(out_dir, 'slope_deg10.tif'), 'w', dtype='int16', nodata=-1, **profile) as f:
        f.write(np.where(valid, np.round(slope * 10), -1).astype(np.int16), 1)
    print(f'elevation: {len(tiles)} tiles; grid of {height} x {width} squares')


def natural_water(hydro_gdb, dams_shp, out_gpkg):
    """Natural water bodies of at least 1 square kilometer, reservoirs removed. Writes out_gpkg."""
    water = gpd.read_file(hydro_gdb, layer='Waterbody').to_crs('ESRI:102003')
    water['km2'] = water.area / 1e6
    dams = gpd.read_file(dams_shp).to_crs('ESRI:102003')
    dams['dam_km2'] = dams['SURF_AREA'] * 0.0040469                   # acres to square kilometers

    # Most reservoirs are called "Lake" in the hydrography. A lake is a reservoir if a major dam at
    # least 40 feet high lies within 3 km and the dam's listed reservoir area is at least a quarter of
    # the lake's area (the listed area is often smaller than the polygon, which shows a fuller pool).
    # Natural lakes with low control dams (Tahoe, Upper Klamath, Utah Lake, Winnebago) stay natural.
    lakes = water[water['Feature'].isin(['Lake', 'Lake Intermittent'])]
    near = gpd.sjoin(lakes[['km2', 'geometry']],
                     gpd.GeoDataFrame(dams[['NID_HEIGHT', 'dam_km2']], geometry=dams.buffer(3000)),
                     predicate='intersects')
    made_by_dam = near.index[(near['NID_HEIGHT'] >= 40) & (near['dam_km2'] >= 0.25 * near['km2'])]
    water['reservoir'] = water.index.isin(set(made_by_dam)) | (water['Feature'] == 'Reservoir')

    natural = water[~water['reservoir']
                    & water['Feature'].isin(['Lake', 'Lake Intermittent', 'Lake Dry', 'Glacier', 'Swamp or Marsh'])
                    & (water['km2'] >= MIN_WATER_KM2)]
    natural[['Name', 'Feature', 'km2', 'geometry']].to_file(out_gpkg)
    print(f'water: {int(water["reservoir"].sum())} reservoirs removed; {len(natural)} natural water bodies kept')


def livable_mask(out_dir, water_gpkg):
    """Livable land on the 250 meter grid: 1 livable, 0 not, 255 outside the elevation data.
    Writes livable_land.tif."""
    with rasterio.open(os.path.join(out_dir, 'elevation_m.tif')) as f:
        elev, profile = f.read(1), f.profile
    with rasterio.open(os.path.join(out_dir, 'slope_deg10.tif')) as f:
        slope = f.read(1) / 10.0
    water = gpd.read_file(water_gpkg).to_crs(profile['crs'])
    in_water = rasterize(((g, 1) for g in water.geometry), out_shape=elev.shape, transform=profile['transform'],
                         fill=0, dtype='uint8').astype(bool)

    livable = ~in_water & ~(elev > MAX_ELEVATION_M) & (slope <= MAX_SLOPE_DEG)
    profile.update(dtype='uint8', nodata=255, compress='deflate')
    with rasterio.open(os.path.join(out_dir, 'livable_land.tif'), 'w', **profile) as f:
        f.write(np.where(elev != -32768, livable.astype('uint8'), 255).astype('uint8'), 1)
    land = (elev != -32768) & (elev > -100)
    print(f'livable share of land: {livable[land].mean():.4f}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inputs', default=os.path.join(ROOT, 'Inputs'))
    parser.add_argument('--out', default=os.path.join(ROOT, 'Intermediate'))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    elevation_and_slope(os.path.join(args.inputs, 'gmted2010'), args.out)
    water_gpkg = os.path.join(args.out, 'natural_water.gpkg')
    natural_water(os.path.join(args.inputs, 'usgs_hydrography', 'hydr48m010g.gdb'),
                  os.path.join(args.inputs, 'usgs_major_dams', 'dams00x020.shp'), water_gpkg)
    livable_mask(args.out, water_gpkg)
    print('saved', os.path.join(args.out, 'livable_land.tif'))


if __name__ == '__main__':
    main()
