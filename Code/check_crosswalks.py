"""Compare a rebuilt crosswalk with a posted one, pair by pair.

Usage:
    python Code/check_crosswalks.py POSTED.csv REBUILT.csv {1990,2010,cz}

It matches rows on the historical county and the reference unit and reports pairs found in only
one file, the largest differences in weights and areas, and rows whose names, ICPSR codes,
merge keys or Union flag differ.
"""
import sys

import pandas as pd


def main(posted, rebuilt, kind):
    codes = ['NHGISST', 'NHGISCTY', f'NHGISST_{kind}', f'NHGISCTY_{kind}', 'GISJOIN', f'GISJOIN_{kind}', f'FIPS_{kind}']
    # Read codes as text so that leading zeros survive.
    a = pd.read_csv(posted, dtype={c: str for c in codes}, low_memory=False)
    b = pd.read_csv(rebuilt, dtype={c: str for c in codes}, low_memory=False)
    print(f"rows: posted {len(a)}, rebuilt {len(b)}; same columns: {list(a.columns) == list(b.columns)}")
    # Match rows on the historical county, the year and the reference unit.
    ref = ['cz'] if kind == 'cz' else [f'NHGISST_{kind}', f'NHGISCTY_{kind}']
    key = ['Year', 'NHGISST', 'NHGISCTY'] + ref
    m = a.merge(b, on=key, how='outer', suffixes=('_posted', '_rebuilt'), indicator=True)
    print(f"pairs only in posted: {(m._merge == 'left_only').sum()}, only in rebuilt: {(m._merge == 'right_only').sum()}")
    both = m[m._merge == 'both']

    # Numbers: report the largest absolute and relative differences.
    for c in ['weight', 'area', 'area_base']:
        diff = (both[c + '_posted'] - both[c + '_rebuilt']).abs()
        rel = diff / both[c + '_posted'].abs()
        print(f"{c}: largest absolute difference {diff.max():.3e}, largest relative difference {rel.max():.3e}")

    # Names, codes and the Union flag: count the rows that differ.
    keys = ['GISJOIN'] + ([] if kind == 'cz' else [f'GISJOIN_{kind}', f'FIPS_{kind}'])
    for c in ['STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY', 'US_STATE'] + [k for k in keys if k + '_posted' in both]:
        x, y = both[c + '_posted'], both[c + '_rebuilt']
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            same = (x == y) | (x.isna() & y.isna())  # 1 and 1.0 count as equal
        else:
            same = (x.astype(str) == y.astype(str)) | (x.isna() & y.isna())
        print(f"{c}: rows that differ {(~same).sum()}")


if __name__ == '__main__':
    main(*sys.argv[1:4])
