"""Write Stata versions of the three crosswalks, with a label on every variable.

    python Code/make_stata_files.py            # reads Crosswalks/*.csv, writes Crosswalks/Stata/*.dta.zip

Each .dta file is zipped to keep the repository small; in Stata, unzipfile unpacks it.

The .dta files hold the same rows and values as the csv files. Codes that need leading zeros
(GISJOIN, GISJOIN_<year>, FIPS_<year>) are text; the NHGIS and ICPSR codes are numbers, as Stata's
import delimited would read them.
"""
import os
import zipfile

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {'county_crosswalk_endyr_1990': '1990', 'county_crosswalk_endyr_2010': '2010', 'cz_crosswalk': None}


def labels(end):
    """Variable labels (at most 80 characters, Stata's limit) for one crosswalk."""
    ref = 'reference commuting zone' if end is None else 'reference county'
    lab = {
        'Year': 'Census year of the historical data',
        'NHGISST': 'NHGIS state code of historical unit',
        'NHGISCTY': 'NHGIS county code of historical unit (FIPS in 2010 rows)',
        'GISJOIN': 'NHGIS GISJOIN code of historical unit',
        'STATENAM': 'State of historical unit',
        'NHGISNAM': 'Name of historical unit',
        'ICPSRST': 'ICPSR state code of historical unit',
        'ICPSRCTY': 'ICPSR county code of historical unit',
        'area_base': 'Area of historical unit, square meters',
        'area': f'Area of historical unit in {ref}, sq. meters',
        'weight': f'Share of historical unit area in {ref}',
        'US_STATE': '1 if historical unit is in a state of the Union',
        'cz': 'Commuting zone of 1990 (Tolbert and Sizer 1996)',
    }
    if end:
        lab.update({
            f'NHGISST_{end}': f'NHGIS state code of {end} county',
            f'NHGISCTY_{end}': f'NHGIS county code of {end} county' if end == '1990' else 'FIPS county code (3 digits) of 2010 county',
            f'STATENAM_{end}': f'State of {end} county',
            f'NHGISNAM_{end}': f'Name of {end} county',
            f'ICPSRST_{end}': f'ICPSR state code of {end} county',
            f'ICPSRCTY_{end}': f'ICPSR county code of {end} county',
            f'GISJOIN_{end}': f'NHGIS GISJOIN code of {end} county',
            f'FIPS_{end}': f'FIPS code (5 digits) of {end} county',
        })
    return lab


def main():
    out_dir = os.path.join(ROOT, 'Crosswalks', 'Stata')
    os.makedirs(out_dir, exist_ok=True)
    for name, end in FILES.items():
        # Read the csv. Codes with leading zeros and names are read as text, everything else as numbers.
        text = ['GISJOIN', f'GISJOIN_{end}', f'FIPS_{end}', 'STATENAM', 'NHGISNAM', f'STATENAM_{end}', f'NHGISNAM_{end}']
        cw = pd.read_csv(os.path.join(ROOT, 'Crosswalks', name + '.csv'), dtype={c: str for c in text}, low_memory=False)
        # Store whole-number columns in the smallest integer type that holds them. Columns with
        # missing values (e.g. the empty ICPSR codes of 2010 counties) stay as floating point.
        for c in cw.columns:
            if c not in text:
                cw[c] = pd.to_numeric(cw[c])
                if c not in ('area', 'area_base', 'weight') and cw[c].notna().all():
                    cw[c] = pd.to_numeric(cw[c], downcast='integer')
        for c in [c for c in text if c in cw.columns]:
            cw[c] = cw[c].fillna('')

        # Write the .dta file with a label on every variable, zip it, and delete the unzipped file.
        lab = labels(end)
        path = os.path.join(out_dir, name + '.dta')
        cw.to_stata(path, write_index=False, version=118, variable_labels={c: lab[c] for c in cw.columns},
                    data_label='EGLP crosswalk, www.fpeckert.me/eglp')
        with zipfile.ZipFile(path + '.zip', 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(path, os.path.basename(path))
        os.remove(path)
        print('wrote', os.path.relpath(path + '.zip', ROOT), len(cw), 'rows')


if __name__ == '__main__':
    main()
