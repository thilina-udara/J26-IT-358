"""Availability/isolation checks for historical feature families."""
import pandas as pd
from ml.training import improve_historical_features as m
from ml.training import train_full_original_dataset as original

def fixture():
    rows=[]
    for district in ['Matara','Hambantota']:
        for year in range(2020,2026):
            for i in range(3):
                rows.append(dict(Record_ID=f'{district}-{year}-{i}',District=district,Crop='Corn',Season='Yala',Year=year,
                    Planting_Date=pd.Timestamp(year,1,1)+pd.Timedelta(days=i),Expected_Harvest_Date=pd.Timestamp(year,4,1)+pd.Timedelta(days=i*14),
                    Land_Size_Acres=float(i+1),Expected_Production_kg=float((i+1)*100)))
    return pd.DataFrame(rows)

def test_historical_feature_prefix_and_district_isolation():
    raw=fixture();f=original.engineer_fast(raw);allfeatures=m.add_features(raw,f)
    earlier=m.add_features(raw[raw.Year<=2024],f[f.Year<=2024])
    pd.testing.assert_frame_equal(earlier.reset_index(drop=True),allfeatures[allfeatures.Year<=2024].reset_index(drop=True))
    changed=raw.copy();changed.loc[changed.District=='Hambantota','Land_Size_Acres']*=100
    actual=m.add_features(changed,original.engineer_fast(changed))
    pd.testing.assert_frame_equal(actual[actual.District=='Matara'].reset_index(drop=True),allfeatures[allfeatures.District=='Matara'].reset_index(drop=True))

def test_features_do_not_read_current_label_components():
    raw=fixture();f=original.engineer_fast(raw);expected=m.add_features(raw,f)
    changed=f.copy();changed['Risk_Label']='High';changed['Overlap_Acres']=999999.;changed['Historical_P33_Acres']=999999.;changed['Historical_P67_Acres']=999999.
    actual=m.add_features(raw,changed);extra=[c for columns in m.FAMILIES.values() for c in columns]
    pd.testing.assert_frame_equal(expected[extra],actual[extra])
