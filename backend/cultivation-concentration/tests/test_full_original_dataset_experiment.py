"""Validate optimized window computation against the established research definition."""
import pandas as pd
from ml.training import train_full_original_dataset as m
from ml.training import train_updated_asc as established

def fixture():
    rows=[]
    for district in ['Matara','Hambantota']:
        for year in range(2020,2027):
            for i,area in enumerate([1.,2.,4.]):
                rows.append(dict(Record_ID=f'{district}-{year}-{i}',District=district,Crop='Corn',Season='Yala',Year=year,
                    Planting_Date=pd.Timestamp(year,1,1)+pd.Timedelta(days=i),
                    Expected_Harvest_Date=pd.Timestamp(year,4,1)+pd.Timedelta(days=14*i),
                    Land_Size_Acres=area*(10 if district=='Hambantota' else 1),Expected_Production_kg=100*area))
    return pd.DataFrame(rows)

def test_optimized_definition_equivalence():
    raw=fixture();reference=established.engineer(raw);fast=m.engineer_fast(raw)
    pd.testing.assert_frame_equal(fast[reference.columns],reference,check_dtype=False)

def test_prefix_availability_and_district_isolation():
    d=fixture();f=m.engineer_fast(d)
    pd.testing.assert_frame_equal(m.engineer_fast(d[d.Year<=2024]).reset_index(drop=True),f[f.Year<=2024].reset_index(drop=True))
    change=d.copy();change.loc[change.District=='Hambantota','Land_Size_Acres']*=100
    actual=m.engineer_fast(change)
    pd.testing.assert_frame_equal(actual[actual.District=='Matara'].reset_index(drop=True),f[f.District=='Matara'].reset_index(drop=True))

def test_historical_harvest_must_precede_actual_cutoff():
    d=fixture();d.loc[d.Year==2021,'Planting_Date']=pd.Timestamp(2020,3,1)
    f=m.engineer_fast(d)
    assert f.loc[f.Year==2021,'Risk_Label'].eq('insufficient_evidence').all()
