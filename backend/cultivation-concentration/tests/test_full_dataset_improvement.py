"""Cutoff and isolation checks for additional historical count features."""
import pandas as pd
from ml.training import improve_full_dataset_xgboost as m
from ml.training import train_full_original_dataset as orig

def fixture():
    rows=[]
    for district in ['Matara','Hambantota']:
        for year in range(2020,2026):
            for i in range(3):
                rows.append(dict(Record_ID=f'{district}-{year}-{i}',District=district,Crop='Corn',Season='Yala',Year=year,
                    Planting_Date=pd.Timestamp(year,1,1)+pd.Timedelta(days=i),Expected_Harvest_Date=pd.Timestamp(year,4,1)+pd.Timedelta(days=i*14),
                    Land_Size_Acres=float(i+1),Expected_Production_kg=float((i+1)*100)))
    return pd.DataFrame(rows)

def test_context_prefix_and_district_isolation():
    d=fixture();f=orig.engineer_fast(d);all_context=m.add_context(d,f)
    earlier=m.add_context(d[d.Year<=2024],f[f.Year<=2024])
    pd.testing.assert_frame_equal(earlier.reset_index(drop=True),all_context[all_context.Year<=2024].reset_index(drop=True))
    changed=d.copy();changed.loc[changed.District=='Hambantota','Land_Size_Acres']*=100
    actual=m.add_context(changed,orig.engineer_fast(changed))
    pd.testing.assert_frame_equal(actual[actual.District=='Matara'].reset_index(drop=True),all_context[all_context.District=='Matara'].reset_index(drop=True))

def test_extra_features_do_not_consume_label_components():
    d=fixture();f=orig.engineer_fast(d);a=m.add_context(d,f)
    f['Risk_Label']='High';f['Overlap_Acres']=999999.;f['Historical_P33_Acres']=999999.;f['Historical_P67_Acres']=999999.
    b=m.add_context(d,f)
    pd.testing.assert_frame_equal(a[m.EXTRA],b[m.EXTRA])
    assert len(m.specs())==13
