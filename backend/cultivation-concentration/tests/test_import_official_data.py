import csv
from ml.preprocessing.import_official_data import COLUMNS, prepare, make_import_sql


def test_selection_and_rejection_without_test_contents(tmp_path):
    path=tmp_path/'fixture.csv'
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(COLUMNS)
        writer.writerow(['Matara','Corn','2010','Maha','2','3'])
        writer.writerow(['DO NOT INSPECT','TEST','2024','BAD','BAD','BAD'])
        writer.writerow(['Matara','Corn','2010','Total','BAD','BAD'])
    rows,skipped,rejected=prepare(path,expected_rows=None)
    assert len(rows)==1 and not rejected and sum(skipped.values())==2
    sql=make_import_sql(rows)
    assert sql.endswith('ROLLBACK;')
    assert 'DO NOT INSPECT' not in sql
    assert 'independent_origin_verified' in sql
    assert 'INSERT INTO c2.availability_evidence(version_id,precision_notes)' in sql
    assert make_import_sql(rows,True).endswith('COMMIT;')


def test_invalid_and_duplicate_rows_rejected(tmp_path):
    path=tmp_path/'fixture.csv'
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(COLUMNS)
        writer.writerows([['Matara','Corn','2010','Maha','2','3']]*2)
        writer.writerow(['Matara','Corn','2011','Maha','NaN','3'])
    rows,_,rejected=prepare(path,expected_rows=None)
    assert len(rows)==1 and len(rejected)==2
