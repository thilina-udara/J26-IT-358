import csv
import pytest
from ml.preprocessing.build_production_reference import build,load_development,save

def row(identity,**changes):
    return dict(dict(Record_ID=identity,District='Matara',Crop='Corn',Year='2020',Season='Maha',Planting_Date='1/1/2020',
        Expected_Harvest_Date='4/1/2020',Land_Size_Acres='2',Expected_Production_kg='200'),**changes)

def test_separation_boundaries_and_identity():
    rows=[row('own'),row('edge',Expected_Harvest_Date='4/15/2020'),row('outside',Expected_Harvest_Date='4/16/2020'),
        row('district',District='Hambantota',Expected_Production_kg='99999'),row('crop',Crop='Brinjal'),row('season',Season='Yala')]
    result=build(rows+[row('own')])
    anchor=next(w for w in result['windows'] if w['scope']=='frozen_reference_2020_2021' and w['half_window_days']==14
        and w['district']=='Matara' and w['crop']=='Corn' and w['season']=='Maha' and w['harvest_anchor']=='2020-04-01')
    assert anchor['plan_count']==2 and anchor['expected_kg']==400 and anchor['acres']==4
    assert result['duplicate_identity_rows_collapsed']==1
    assert result['unique_plan_count']==6
    with pytest.raises(ValueError):build([row('own'),row('own',Land_Size_Acres='5')])

def test_isolation_and_frozen_reference(tmp_path):
    source=tmp_path/'fictional.csv';fields=list(row('a'))
    with source.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerow(row('a'));writer.writerow(row('sealed',Year='2024',Expected_Harvest_Date='DO_NOT_PARSE',Expected_Production_kg='DO_NOT_PARSE'))
    selected,excluded=load_development(source)
    assert len(selected)==1 and excluded==1
    result=build(selected+[row('later',Year='2022',Expected_Harvest_Date='4/1/2020',Expected_Production_kg='999')])
    assert all(w['expected_kg']==200 for w in result['windows'] if w['scope']=='frozen_reference_2020_2021')
    with pytest.raises(ValueError):build([row('sealed',Year='2024')])

def test_determinism_quantiles_and_safe_reruns(tmp_path):
    rows=[row('a'),row('b',Expected_Harvest_Date='4/15/2020')]
    first=build(rows);second=build(list(reversed(rows)))
    assert first==second
    path,status=save(first,tmp_path);assert status=='created'
    before=path.read_bytes()
    assert save(second,tmp_path)[1]=='identical_existing_preserved'
    assert path.read_bytes()==before
    assert all(d['independent_sample_size'] is None for d in first['reference_distributions'])
    assert {w['half_window_days'] for w in first['windows']}=={7,14,21}
