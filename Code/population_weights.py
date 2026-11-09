"""Compute the livable-area and population-based weights for one reference map.

Used by crosswalk_county_population.py and crosswalk_cz_population.py, which add the weights to the
crosswalk files. Needs the map of livable land (livable_land.py) and the list of towns (towns.py).

The weights split each historical county's census population, not its land, across the units of the
reference map. The method:
  1. A grid of 500 by 500 meter cells covers the contiguous United States. Each cell records its
     county in every census year (the maps are rasterized at cell centers) and the share of its land
     that is livable.
  2. Each year, the towns of the town list sit at their GNIS points, in the nearest cell (within 10 km)
     that lies in the same county of that year and of 2010 as the point, in the town's own state, and
     inside the town's own "<town> city" census unit if that year has one. Where a county's towns add up
     to more than its census count, they are scaled down to it.
  3. 2010: each county's people outside towns (its rural population) are spread evenly over its livable land.
  4. Going back one census at a time, each county's rural population is spread over its cells in
     proportion to the rural population of the same cells at the next census. Cells in a county whose
     people at the next census were 99% or more in towns carry no information on the rural population;
     they get the average rural population per unit of livable land of the rest of their county.
  5. Thin border strips. The historical maps and the reference map do not trace the same county lines
     exactly, so almost every county has thin strips along its border that fall in a neighboring unit of
     the reference map. On the grid such a strip can hold a few cells and their people. A piece of a
     county counts as such a strip if none of its cells lies more than 1 km from a line between two
     counties on either map (shores do not count, so islands are kept). A strip without a town gets no
     people, and the county's other pieces are scaled up to keep its total.
  6. The weight of a unit of the reference map is the share of the county's people placed in it
     (population-based weights) or the share of the county's livable land in it (livable-area weights;
     steps 1 and 5 only). A county without a census count gets the share of its cells as population-based
     weights, and a county without livable land the share of its cells as livable-area weights. Weights
     under one in a million are set to 0 and the others rescaled.

Data corrections (each a census fact; the corrections to the town list are in towns.py):
  - census counts that the NHGIS table lacks for the District of Columbia (1800, 1820, 1860, 1880, 1900);
  - map units that the census counts inside a neighbor: Baltimore City 1870 in Baltimore County,
    Williamsburg 1910-1920 in James City County;
  - Petersburg, VA, counted inside Dinwiddie (1790, 1840-1880); Trenton, NJ, inside Hunterdon (1810-1830);
  - Alexandria city, VA, 1900 has a census count but no polygon on the 1900 map; it gets its own row,
    all to Alexandria city;
  - New Orleans suburbs counted in Jefferson Parish, 1840-1860 (Lafayette 1840 3,207 and 1850 14,190;
    Jefferson City 1860 5,107), while the maps draw Orleans at its 2010 extent: their share of Jefferson
    moves to Orleans in the population-based weights.
"""
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt

from crosswalk_county import read_year

YEARS = list(range(1790, 2011, 10))
ALL_TOWN = 0.99             # share of a county's people in towns above which it has no rural information
SNAP_CELLS = 20             # towns move at most 20 cells (10 km) to reach the right county
STRIP_KM = 1                # border strips: no cell more than 1 km from a county line
MIN_WEIGHT = 1e-6           # smaller weights are set to 0

# Census counts that the NHGIS table lacks
DC_COUNTS = {1800: 14093, 1820: 33039, 1860: 75080, 1880: 177624, 1900: 278718}
DC_UNIT = {1800: 1100015, 1820: 1100015, 1860: 1100010, 1880: 1100010, 1900: 1100010}
# Map units that the census counts inside a neighbor: {year: {unit: the unit it is counted in}}
# (ids NHGISST * 10000 + NHGISCTY)
COUNTED_IN = {1870: {2405100: 2400050},   # Baltimore City, counted in Baltimore County
              1910: {5108300: 5100950},   # Williamsburg, counted in James City County
              1920: {5108300: 5100950}}
# Towns that the census counts inside another county
TOWN_IN = {('Petersburg', 'VA'): {y: 5100530 for y in (1790, 1840, 1850, 1860, 1870, 1880)},   # in Dinwiddie
           ('Trenton', 'NJ'): {y: 3400190 for y in (1810, 1820, 1830)}}                         # in Hunterdon
# State FIPS codes by postal abbreviation; IT is Indian Territory, today's Oklahoma.
FIPS = {'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11',
        'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21',
        'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29', 'MT': '30',
        'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
        'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49',
        'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56', 'IT': '40'}


def people_by_piece(shapefile_dir, state_names, livable_tif, pop_csv, towns_gpkg, reference, cz_shp=None):
    """People by piece (a county of a census year and a unit of the reference map), steps 1-4.

    reference: '2010' (2010 counties), '1990' (1990 counties) or 'cz' (1990 commuting zones, which needs
    cz_shp). Returns one row per piece: year, cstart (the county of that year), cref (the unit of the
    reference map), cells, county_pop (the county's census count), livable (its livable land, in cells),
    pop_towns (people in listed towns), pop_towns_cascade (all its people placed
    by steps 2-4) and depth (how far in km the piece reaches from the nearest line between two counties)."""

    # ---- the grid: 500 m cells, each the average of four 250 m squares of livable land
    with rasterio.open(livable_tif) as f:
        m = f.read(1)
        t250, crs = f.transform, f.crs
    h, w = m.shape[0] // 2, m.shape[1] // 2
    m = m[:2 * h, :2 * w].astype(np.float32)
    m[m == 255] = 1.0                       # cells outside the elevation data count as livable
    livable = m.reshape(h, 2, w, 2).mean(axis=(1, 3)).ravel()
    del m
    transform = Affine(t250.a * 2, 0, t250.c, 0, t250.e * 2, t250.f)

    def to_cells(x, y):
        """Grid cell of each projected point, and whether it lies on the grid."""
        col, row = ~transform * (x, y)
        col, row = np.floor(col).astype(int), np.floor(row).astype(int)
        on = (row >= 0) & (row < h) & (col >= 0) & (col < w)
        return np.where(on, row * w + col, 0), on

    # ---- census counts, towns
    pop = pd.read_csv(pop_csv, encoding='latin-1', low_memory=False)
    pop['id'] = pop['STATENH'].astype(int) * 10000 + pop['COUNTYNH'].astype(int)
    for y, v in DC_COUNTS.items():
        pop.loc[pop['id'] == DC_UNIT[y], f'A00AA{y}'] = v

    towns = gpd.read_file(towns_gpkg)
    town_cell, town_on_grid = to_cells(towns.geometry.x.values, towns.geometry.y.values)
    town_state = towns['ST'].map({k: int(v) for k, v in FIPS.items()}).fillna(0).astype(int).values

    city_units = {}     # year -> {(state FIPS, lowercase town name): id of the census unit "<town> city"}
    point_county = {}   # year -> the county each town's exact point lies in (0 if none)

    def county_ids(y):
        """County id of every cell in census year y (NHGISST * 10000 + NHGISCTY; 2010: state * 100000 + county * 10)."""
        g = read_year(shapefile_dir, str(y), state_names).reset_index(drop=True)
        g['cid'] = g['NHGISST'].astype(int) * 10000 + g['NHGISCTY'].astype(int) * (10 if y == 2010 else 1)
        for unit, into in COUNTED_IN.get(y, {}).items():
            g.loc[g['cid'] == unit, 'cid'] = into
        j = gpd.sjoin(towns[['geometry']].to_crs(g.crs), g[['cid', 'geometry']], predicate='within')
        point_county[y] = j[~j.index.duplicated()]['cid'].reindex(towns.index).fillna(0).astype(int).values
        names = g['NHGISNAM'].astype(str).str.lower().str.strip()
        city = names.str.endswith(' city')
        city_units[y] = {(st // 10, n[:-5].strip()): i for st, n, i in
                         zip(g['NHGISST'].astype(int)[city], names[city], g['cid'][city])}
        return rasterize(zip(g.geometry, g['cid']), out_shape=(h, w), transform=transform, fill=0,
                         dtype='int32').ravel()

    def nearest(cells, r0, c0):
        """The cell of `cells` nearest to row r0, column c0."""
        rows, cols = np.divmod(cells, w)
        return cells[((rows - r0) ** 2 + (cols - c0) ** 2).argmin()]

    def town_people(y, ids):
        """People in listed towns per cell in year y."""
        v = towns[f'pop{y}'].values
        sel = np.where(town_on_grid & (v > 0))[0]
        cells = town_cell[sel].copy()
        for k, i in enumerate(sel):
            # the county the town belongs to this year (its point's, unless the census counted it elsewhere) and in 2010
            cy = TOWN_IN.get((towns['City'].iloc[i], towns['ST'].iloc[i]), {}).get(y, point_county[y][i])
            c10 = point_county[2010][i]
            in_2010 = (lambda c: ids2010[c] == c10) if c10 else (lambda c: ids2010[c] > 0)   # point off the 2010 map:
            right_county = (ids[cells[k]] > 0) if cy == 0 else (ids[cells[k]] == cy)       # any 2010 county will do
            if right_county and in_2010(cells[k]):
                continue
            r0, c0 = divmod(cells[k], w)
            rr, cc = np.mgrid[max(r0 - SNAP_CELLS, 0):min(r0 + SNAP_CELLS + 1, h),
                              max(c0 - SNAP_CELLS, 0):min(c0 + SNAP_CELLS + 1, w)]
            cand, d2 = (rr * w + cc).ravel(), ((rr - r0) ** 2 + (cc - c0) ** 2).ravel()
            # NHGIS state codes are state FIPS * 10 (states) or * 10 + 5 (territories); codes that end in another
            # digit (Indian Territory 178, Orleans Territory 417, Oregon Territory 413) and Dakota Territory 95
            # cannot be compared with the town's state and are not checked
            st, code = town_state[i] * 10, cy // 10000
            comparable = code % 10 in (0, 5) and code != 95
            if cy == 0:                                          # point in no county (offshore): nearest land
                ok = (ids[cand] > 0) & in_2010(cand) & np.isin(ids[cand] // 10000, (st, st + 5))   # cell of its state
            elif code in (st, st + 5) or not comparable:
                both = (ids[cand] == cy) & in_2010(cand)
                ok = both if both.any() else (ids[cand] == cy)
            else:                                                # the point lies in another state on this year's map
                ok = np.isin(ids[cand] // 10000, (st, st + 5))
            if ok.any():
                cells[k] = cand[ok][d2[ok].argmin()]
        for k, i in enumerate(sel):                              # a town goes into its own "<town> city" census unit
            unit = city_units[y].get((town_state[i], towns['City'].iloc[i].lower()))
            if unit is not None and unit != ids[cells[k]]:
                unit_cells = np.where(ids == unit)[0]
                if len(unit_cells):
                    cells[k] = nearest(unit_cells, *divmod(cells[k], w))
        lost = (ids[cells] == 0) | (ids2010[cells] == 0)
        if lost.any():
            raise SystemExit(f'{y}: towns placed in a cell without a county: '
                             f'{towns.iloc[sel[lost]][["City", "ST"]].values.tolist()}')
        return np.bincount(cells, weights=v[sel], minlength=h * w)

    def split(ids, census, town_pop, guide):
        """Towns at their cells (scaled down where they exceed the county's census count); each county's other
        people over its cells in proportion to guide (evenly if the guide is zero everywhere in the county)."""
        uid, inv = np.unique(ids, return_inverse=True)
        towns_total = np.bincount(inv, weights=town_pop)
        total = pd.Series(census).reindex(uid).fillna(0).to_numpy(dtype=float, copy=True)
        total[uid == 0] = 0
        town_pop = town_pop * np.where(towns_total > total, total / np.where(towns_total > 0, towns_total, 1), 1.0)[inv]
        rest = total - np.minimum(towns_total, total)
        guide_total, n = np.bincount(inv, weights=guide), np.bincount(inv)
        share = np.where(guide_total[inv] > 0, guide / np.where(guide_total[inv] > 0, guide_total[inv], 1), 1.0 / n[inv])
        return town_pop, rest[inv] * share

    def rural_guide(ids, ids_next, rural_next, towns_next):
        """The guide for spreading year y's rural population: the rural population at the next census, except in
        counties that were all towns at the next census, which get the average rural density of the rest of
        their county."""
        _, inv_next = np.unique(ids_next, return_inverse=True)
        rural_c, towns_c = np.bincount(inv_next, weights=rural_next), np.bincount(inv_next, weights=towns_next)
        no_info = (rural_c[inv_next] <= (1 - ALL_TOWN) * (rural_c + towns_c)[inv_next]) & (ids_next > 0)
        uid, inv = np.unique(ids, return_inverse=True)
        known = ~no_info
        density = np.bincount(inv, weights=rural_next * known) / np.maximum(np.bincount(inv, weights=livable * known), 1e-12)
        return np.where(no_info, np.where(density[inv] > 0, density[inv] * livable, livable), rural_next)

    def depth(*maps):
        """For each cell, its distance in km to the nearest line between two counties on any of the maps (a cell
        next to a line: 0.5 km). Shores do not count, so an island is not a strip."""
        edge = np.zeros((h, w), dtype=bool)
        for ids in maps:
            g = ids.reshape(h, w)
            d = (g[:, 1:] != g[:, :-1]) & (g[:, 1:] > 0) & (g[:, :-1] > 0)
            edge[:, 1:] |= d
            edge[:, :-1] |= d
            d = (g[1:, :] != g[:-1, :]) & (g[1:, :] > 0) & (g[:-1, :] > 0)
            edge[1:, :] |= d
            edge[:-1, :] |= d
        return (distance_transform_edt(~edge).ravel() + 1) * transform.a / 1000

    def pieces(y, ids, ref, census, town_pop, rural_pop):
        """People by piece of year y's counties and the reference map."""
        zero = np.zeros_like(livable)
        cells = pd.DataFrame({'year': y, 'cstart': ids, 'cref': ref, 'cells': 1,
                              'county_pop': pd.Series(census).reindex(ids).fillna(0).to_numpy(),
                              'pop_area': split(ids, census, zero, np.ones_like(livable))[1],
                              'livable': livable.astype(np.float64),     # summed in double precision
                              'pop_towns': town_pop, 'pop_towns_cascade': town_pop + rural_pop, 'depth': depth(ids, ref)})
        cells = cells[(cells['cstart'] > 0) & (cells['cref'] > 0)]
        return cells.groupby(['year', 'cstart', 'cref'], as_index=False).agg(
            cells=('cells', 'sum'), county_pop=('county_pop', 'first'), pop_area=('pop_area', 'sum'),
            livable=('livable', 'sum'), pop_towns=('pop_towns', 'sum'),
            pop_towns_cascade=('pop_towns_cascade', 'sum'), depth=('depth', 'max'))

    # ---- the reference map (ids of the cells)
    ids2010 = county_ids(2010)
    if reference == '2010':
        ref = ids2010
    elif reference == '1990':
        ref = county_ids(1990)
    else:
        # Commuting zones are unions of 1990 counties, but cz1990.shp does not trace the NHGIS 1990 lines or
        # coast. Each 1990 county gets the zone that covers most of its cells, and every cell of the county
        # gets that zone.
        c1990 = county_ids(1990)
        cz = gpd.read_file(cz_shp).to_crs(crs)
        cz_cells = rasterize(zip(cz.geometry, cz['cz'].astype(int)), out_shape=(h, w), transform=transform, fill=0,
                             dtype='int32').ravel()
        c = pd.DataFrame({'c1990': c1990, 'cz': cz_cells})
        c = c[(c['c1990'] > 0) & (c['cz'] > 0)].value_counts().rename('n').reset_index()
        c['share'] = c['n'] / c.groupby('c1990')['n'].transform('sum')
        c = c.sort_values('n', ascending=False).drop_duplicates('c1990')
        missing = set(np.unique(c1990)) - set(c['c1990']) - {0}
        if missing:
            raise SystemExit(f'1990 counties without a commuting zone: {sorted(missing)}')
        ref = pd.Series(c['cz'].values, index=c['c1990'].values).reindex(c1990).fillna(0).astype('int32').to_numpy()
        del cz_cells

    # ---- 2010, then back one census at a time
    out = []
    census = pop.set_index('id')['A00AA2010'].dropna()
    town_pop, rural_pop = split(ids2010, census, town_people(2010, ids2010), livable)
    if reference != '2010':                    # 2010 counties are not mapped onto themselves
        out.append(pieces(2010, ids2010, ref, census, town_pop, rural_pop))
    ids_next, towns_next = ids2010, town_pop
    for y in reversed(YEARS[:-1]):
        ids = county_ids(y)
        census = pop.set_index('id')[f'A00AA{y}'].dropna()
        guide = rural_guide(ids, ids_next, rural_pop, towns_next)
        town_pop, rural_pop = split(ids, census, town_people(y, ids), guide)
        ids_next, towns_next = ids, town_pop
        if reference != str(y):                # 1990 counties are not mapped onto themselves
            out.append(pieces(y, ids, ref, census, town_pop, rural_pop))
        print(y, 'done', flush=True)
    return pd.concat(out)


def drop_border_strips(d, km=STRIP_KM):
    """Step 5: a piece that reaches no more than km from a county line and holds no town gets no people; the
    county's other pieces are scaled up to keep its total. Applies to the population-based and the
    livable-area weights."""
    d = d.reset_index(drop=True)
    g = d.groupby(['year', 'cstart'])
    strip = (d['depth'] <= km + 1e-9) & (d['pop_towns'] <= 0) & (g['cells'].transform('size') > 1)
    for col in ['pop_towns_cascade', 'livable']:
        total = d.groupby(['year', 'cstart'])[col].transform('sum')
        d.loc[strip, col] = 0
        kept = d.groupby(['year', 'cstart'])[col].transform('sum')
        d[col] = d[col] * (total / kept.where(kept > 0, 1)).where(kept > 0, 1)
    print(f'{int(strip.sum()):,} of {len(d):,} pieces are border strips without a town')
    return d


def gisjoin(cid):
    """GISJOIN of a county on the NHGIS maps of 1790-2000, from its id NHGISST * 10000 + NHGISCTY."""
    return 'G' + (cid // 10000).map('{:03d}'.format) + (cid % 10000).map('{:04d}'.format)


def weights(d, reference):
    """Step 6: the weights, one row per piece: year, GISJOIN of the historical county, the unit of the
    reference map (GISJOIN_1990, GISJOIN_2010 or cz), county_pop, weight_livable, weight_population."""
    d = d.copy()
    d['GISJOIN'] = gisjoin(d['cstart'])
    if reference == '2010':                    # 2010 ids: state * 100000 + county * 10
        st, co = d['cref'] // 100000, (d['cref'] % 100000) // 10
        key = 'GISJOIN_2010'
        d[key] = 'G' + st.map('{:02d}'.format) + '0' + co.map('{:03d}'.format) + '0'
    elif reference == '1990':
        key = 'GISJOIN_1990'
        d[key] = gisjoin(d['cref'])
    else:
        key = 'cz'
        d[key] = d['cref']

    g = d.groupby(['year', 'cstart'])
    cells = g['cells'].transform('sum')
    for col, w in [('pop_towns_cascade', 'weight_population'), ('livable', 'weight_livable')]:
        total = g[col].transform('sum')
        d[w] = np.where(total > 0, d[col] / total.where(total > 0, 1), d['cells'] / cells)
    d['weight_area'] = d['cells'] / cells      # the share of the county's cells, used only to keep rows below
    d['county_pop'] = d['county_pop'].round().astype(int)
    census = d.groupby(['year', 'GISJOIN'])['county_pop'].first()
    W = ['weight_population', 'weight_livable', 'weight_area']
    out = d[['year', 'GISJOIN', key, 'county_pop'] + W].copy()
    for w in ['weight_population', 'weight_livable']:
        out[w] = out[w].where(out[w] >= MIN_WEIGHT, 0)
    out = out[(out['weight_population'] > 0) | (out['weight_livable'] > 0) | (out['weight_area'] >= MIN_WEIGHT)]
    for w in W:
        out[w] = out[w] / out.groupby(['year', 'GISJOIN'])[w].transform('sum')

    # Alexandria city, VA, 1900: a census count but no polygon on the 1900 map
    alexandria = {'GISJOIN_2010': 'G5105100', 'GISJOIN_1990': 'G5105100', 'cz': 11304}[key]
    out = pd.concat([out, pd.DataFrame([{'year': 1900, 'GISJOIN': 'G5105100', key: alexandria, 'county_pop': 14528,
                                         'weight_population': 1.0, 'weight_livable': 1.0, 'weight_area': 1.0}])])
    # New Orleans suburbs counted in Jefferson Parish: their share of Jefferson moves to Orleans
    orleans_unit = {'GISJOIN_2010': 'G2200710', 'GISJOIN_1990': 'G2200710', 'cz': 3300}[key]
    for y, suburbs in {1840: 3207, 1850: 14190, 1860: 5107}.items():
        jefferson = (out['year'] == y) & (out['GISJOIN'] == 'G2200510')
        share = suburbs / census[(y, 'G2200510')]
        out.loc[jefferson, 'weight_population'] *= 1 - share
        orleans = jefferson & (out[key] == orleans_unit)
        if orleans.any():
            out.loc[orleans, 'weight_population'] += share
        else:
            out = pd.concat([out, out[jefferson].iloc[[0]].assign(**{key: orleans_unit}, weight_population=share,
                                                                  weight_livable=0.0, weight_area=0.0)])
    for w in ['weight_population', 'weight_livable']:
        assert np.allclose(out.groupby(['year', 'GISJOIN'])[w].sum(), 1), f'{w} must sum to 1'
    return out.drop(columns='weight_area').rename(columns={'year': 'Year'})


def add_to_crosswalk(path, w, key):
    """Add the columns weight_livable and weight_population to the crosswalk file at path, after weight.

    The file is read and written as text, so its other columns stay exactly as they are. A row of the file
    that the weights do not reach (a thin sliver between two maps' lines) gets 0. Rows of counties outside
    the contiguous United States (Alaska and Hawaii) are left empty, as are county-years without weights.
    A piece that the file lacks gets a row of its own, with the historical county's columns copied from the
    file and an area weight of 0 (or empty for Alexandria city 1900, which has no polygon)."""
    cw = pd.read_csv(path, dtype=str, keep_default_na=False)
    cw = cw.drop(columns=[c for c in ('weight_livable', 'weight_population') if c in cw.columns])
    w = w.copy()
    w['Year'] = w['Year'].astype(str)
    w[key] = w[key].astype(str)
    for c in ('weight_livable', 'weight_population'):
        w[c] = w[c].map('{:.8g}'.format)
    cw['_order'] = np.arange(len(cw), dtype=float)

    m = cw.merge(w[['Year', 'GISJOIN', key, 'weight_livable', 'weight_population']], on=['Year', 'GISJOIN', key],
                 how='left', indicator=True)
    covered = set(zip(w['Year'], w['GISJOIN']))
    has_weights = pd.Series(list(zip(m['Year'], m['GISJOIN'])), index=m.index).isin(covered)
    for c in ('weight_livable', 'weight_population'):
        m[c] = m[c].where(m['_merge'] == 'both', np.where(has_weights, '0', ''))

    # pieces that the file lacks
    new = w.merge(cw[['Year', 'GISJOIN', key]], on=['Year', 'GISJOIN', key], how='left', indicator=True)
    new = new[new['_merge'] == 'left_only']
    rows = []
    hist = [c for c in cw.columns if c in ('Year', 'NHGISST', 'NHGISCTY', 'GISJOIN', 'STATENAM', 'NHGISNAM', 'ICPSRST',
                                           'ICPSRCTY', 'area_base', 'US_STATE')]
    ref_cols = [c for c in cw.columns if c.endswith(('_1990', '_2010')) or c == 'cz']
    for _, r in new.iterrows():
        same_county = cw[(cw['Year'] == r['Year']) & (cw['GISJOIN'] == r['GISJOIN'])]
        same_unit = cw[cw[key] == r[key]]
        if len(same_county):                   # a county of the file: copy its columns, area weight 0
            row = same_county.iloc[0][hist].to_dict()
            row.update(area='0', weight='0', _order=same_county['_order'].max() + 0.5)
        else:                                  # Alexandria city 1900: copied from its earliest row
            later = cw[cw['GISJOIN'] == r['GISJOIN']].sort_values('Year').iloc[0]
            row = later[hist].to_dict()
            row.update(Year=r['Year'], area_base='', area='', weight='',
                       _order=cw.loc[cw['Year'] == r['Year'], '_order'].max() + 0.5)
        row.update(same_unit.iloc[0][ref_cols].to_dict())
        row.update(weight_livable=r['weight_livable'], weight_population=r['weight_population'])
        rows.append(row)
    if rows:
        m = pd.concat([m, pd.DataFrame(rows)], ignore_index=True)

    cols = [c for c in cw.columns if c != '_order']
    i = cols.index('weight') + 1
    cols = cols[:i] + ['weight_livable', 'weight_population'] + cols[i:]
    m = m.sort_values('_order', kind='stable')[cols]
    m.to_csv(path, index=False)
    print(f'{os.path.basename(path)}: {len(m):,} rows, {len(rows)} new; weights on '
          f'{(m["weight_population"] != "").sum():,} rows; empty on {(m["weight_population"] == "").sum():,}')
