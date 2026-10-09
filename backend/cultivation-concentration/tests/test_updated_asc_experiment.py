"""Safety checks for the separate authoritative-CSV experiment."""
import pandas as pd
from ml.training import train_updated_asc as m

def fixture():
    rows=[]
    for year in range(2020,2027):
        for i,area in enumerate((1.,2.,4.)):
            rows.append(dict(Record_ID=f'{year}-{i}',District='Matara',Crop='Corn',Season='Yala',Year=year,
                Planting_Date=pd.Timestamp(year,1,1),Expected_Harvest_Date=pd.Timestamp(year,4+i,1),
                Land_Size_Acres=area,Expected_Production_kg=area*100))
    return pd.DataFrame(rows)

def test_updated_cutoffs_and_district_isolation():
    d=fixture();f=m.engineer(d)
    assert f.loc[f.Year==2020,'Risk_Label'].eq('insufficient_evidence').all()
    changed=d.copy();changed.loc[changed.Year==2026,'Land_Size_Acres']*=100
    pd.testing.assert_frame_equal(m.engineer(changed).loc[f.Year<2026],f.loc[f.Year<2026])
    other=d.copy();other['District']='Hambantota';other['Record_ID']='other-'+other.Record_ID;other['Land_Size_Acres']*=100
    result=m.engineer(pd.concat([d,other],ignore_index=True))
    pd.testing.assert_frame_equal(result[result.District=='Matara'].reset_index(drop=True),f)
    assert (f.Reference_Latest_Harvest.dropna()<f.loc[f.Reference_Latest_Harvest.notna(),'Prediction_Cutoff']).all()

def test_prior_season_planting_does_not_use_future_history():
    d=fixture()
    d.loc[d.Year==2021,'Planting_Date']=pd.Timestamp(2020,3,1)
    f=m.engineer(d)
    assert f.loc[f.Year==2021,'Risk_Label'].eq('insufficient_evidence').all()
