"""Add ready-made merge keys to a crosswalk.

GISJOIN is the identifier NHGIS puts in every county data extract and shapefile:
"G", the three-digit NHGIS state code and the four-digit NHGIS county code, e.g. G0100010
for Autauga County, Alabama. It is added for the historical unit (GISJOIN) and, in the county
crosswalks, for the reference county (GISJOIN_1990, GISJOIN_2010).

FIPS_1990 and FIPS_2010 are the five-digit FIPS codes of the reference county (two-digit state,
three-digit county, e.g. 01001), as text with leading zeros, the form most modern data use.

The codes are computed from the NHGIS codes already in the file. For every county map from
1790 to 2010 they equal the GISJOIN column of the NHGIS shapefile.
"""


def _digits(col, width):
    return col.astype(float).astype(int).astype(str).str.zfill(width)


def add_merge_keys(cw, end=None):
    """cw: a crosswalk DataFrame. end: '1990' or '2010' for the county crosswalks, None for commuting zones.
    Returns a copy with the new columns placed next to the codes they are built from."""
    cw = cw.copy()
    cols = list(cw.columns)
    cw['GISJOIN'] = 'G' + _digits(cw['NHGISST'], 3) + _digits(cw['NHGISCTY'], 4)
    # in the rows for 2010, NHGISCTY holds the three-digit FIPS county code, as in the 2010 shapefile
    y2010 = cw['Year'].astype(int) == 2010
    cw.loc[y2010, 'GISJOIN'] = 'G' + _digits(cw.loc[y2010, 'NHGISST'], 3) + _digits(cw.loc[y2010, 'NHGISCTY'], 3) + '0'
    new_cols = cols[:cols.index('NHGISCTY') + 1] + ['GISJOIN'] + cols[cols.index('NHGISCTY') + 1:]
    if end is not None:
        st, cty = cw[f'NHGISST_{end}'], cw[f'NHGISCTY_{end}']
        if end == '1990':     # NHGIS codes: FIPS with a zero appended
            assert (cty.astype(float).astype(int) % 10 == 0).all() and (st.astype(float).astype(int) % 10 == 0).all()
            fips_st, fips_cty = st.astype(float).astype(int) // 10, cty.astype(float).astype(int) // 10
        else:                 # 2010: NHGIS state code, three-digit FIPS county code
            fips_st, fips_cty = st.astype(float).astype(int) // 10, cty.astype(float).astype(int)
        cw[f'FIPS_{end}'] = fips_st.astype(str).str.zfill(2) + fips_cty.astype(str).str.zfill(3)
        cw[f'GISJOIN_{end}'] = 'G' + fips_st.astype(str).str.zfill(2) + '0' + fips_cty.astype(str).str.zfill(3) + '0'
        i = new_cols.index(f'ICPSRCTY_{end}') + 1
        new_cols = new_cols[:i] + [f'GISJOIN_{end}', f'FIPS_{end}'] + new_cols[i:]
    return cw[new_cols]
