"""Fictional training fixtures and loading the separately authorized experiment artifact."""
import joblib
import numpy as np
import pandas as pd
import pytest
from ml.training import train_asc_2020_2026 as m


def raw():
    rows=[]
    for year in range(2020,2027):
        for i,area in enumerate((1.,2.,4.)):
            rows.append(dict(Record_ID=f'{year}-{i}',District='Matara',Crop='Corn',Season='Yala',Year=year,
                Planting_Date=f'1/1/{year}',Expected_Harvest_Date=f'{4+i}/1/{year}',Land_Size_Acres=area,
                Expected_Yield_kg_per_Acre=100,Expected_Production_kg=area*100))
    return pd.DataFrame(rows)


def loaded(tmp_path):
    a=tmp_path/'first.csv';b=tmp_path/'second.csv';data=raw()
    data.loc[data.Year<=2025].to_csv(a,index=False);data.loc[data.Year==2026].to_csv(b,index=False)
    return m.load([a,b]),a,b


def test_merge_duplicate_validation(tmp_path):
    (data,audit),a,b=loaded(tmp_path)
    assert len(data)==21 and audit['production_formula_mismatch_count']==0
    pd.concat([raw().iloc[:1],raw().loc[raw().Year==2026]]).to_csv(b,index=False)
    data,audit=m.load([a,b]);assert len(data)==21 and audit['exact_duplicates_removed']==1
    changed=raw().iloc[:1].copy();changed['Land_Size_Acres']=5
    changed.to_csv(b,index=False)
    with pytest.raises(ValueError,match='duplicate plan ID'):m.load([a,b])


def test_chronology_no_future_leakage_and_district_isolation(tmp_path):
    (data,_),_,_=loaded(tmp_path)
    engineered=m.engineer(data);train,val,test=m.split(engineered)
    assert set(train.Year)=={2021,2022,2023,2024} and set(val.Year)=={2025} and set(test.Year)=={2026}
    assert not set(train.Record_ID)&set(val.Record_ID) and not set(val.Record_ID)&set(test.Record_ID)
    changed=data.copy();changed.loc[changed.Year>=2025,'Land_Size_Acres']=999
    pd.testing.assert_frame_equal(m.engineer(changed).loc[engineered.Year<=2024],engineered.loc[engineered.Year<=2024])
    other=data.copy();other['District']='Hambantota';other['Record_ID']='other-'+other.Record_ID;other['Land_Size_Acres']=999
    combined=m.engineer(pd.concat([data,other],ignore_index=True))
    pd.testing.assert_frame_equal(combined.loc[combined.District=='Matara'].reset_index(drop=True),engineered)
    assert not set(m.FEATURES)&{'Risk_Label','Overlap_Acres','Overlap_Expected_Production_kg','Historical_P33_Acres','Historical_P67_Acres','Year','Record_ID'}


def test_preprocessing_reproducibility_and_artifact_loading(tmp_path):
    (data,_),_,_=loaded(tmp_path)
    train,val,_=m.split(m.engineer(data))
    y=train.Risk_Label.map(dict(zip(m.LABELS,range(3))))
    first=m.models()['Random Forest'];second=m.models()['Random Forest']
    first.fit(m.inputs(train),y);second.fit(m.inputs(train),y)
    assert np.array_equal(first.predict(m.inputs(val)),second.predict(m.inputs(val)))
    path=tmp_path/'fixture.joblib';joblib.dump(first,path)
    restored=joblib.load(path)
    assert np.array_equal(first.predict(m.inputs(val)),restored.predict(m.inputs(val)))
    medians=first.named_steps['preprocessing'].named_transformers_['num'].named_steps['impute'].statistics_
    assert np.allclose(medians,train[m.NUM].median().to_numpy())


def test_inclusive_overlap_and_same_date_exclusion(tmp_path):
    (data,_),_,_=loaded(tmp_path)
    peers=data.iloc[:1].copy();peers['Record_ID']='boundary';peers['Planting_Date']=pd.Timestamp(2020,1,2)
    peers['Expected_Harvest_Date']=pd.Timestamp(2020,4,15)
    result=m.engineer(pd.concat([data,peers],ignore_index=True))
    assert result.iloc[-1].Overlap_Plan_Count==2 and result.iloc[-1].Overlap_Acres==2
    peers['Expected_Harvest_Date']=pd.Timestamp(2020,4,16)
    assert m.engineer(pd.concat([data,peers],ignore_index=True)).iloc[-1].Overlap_Plan_Count==1
    peers['Planting_Date']=pd.Timestamp(2020,1,1)
    assert m.engineer(pd.concat([data,peers],ignore_index=True)).iloc[-1].Overlap_Plan_Count==1


def test_saved_pp1_models_load_with_feature_schema():
    import json
    root=m.ROOT/'models/experimental'
    context=pd.read_csv(root/'historical_feature_improvement/v1_20261009/features_and_labels_2020_2025.csv')
    row=context.loc[lambda d:(d.Year==2025)&d.Risk_Label.isin(m.LABELS)].iloc[:1]
    bundles=[('full_original_dataset','random_forest_through_2024.joblib','random_forest_preprocessing_through_2024.joblib'),
             ('historical_feature_improvement','selected_xgboost_through_2024.joblib','selected_preprocessing_through_2024.joblib')]
    for folder,artifact,preprocessing in bundles:
        directory=root/folder/'v1_20261009'
        features=json.loads((directory/'feature_schema.json').read_text())['features']
        assert not set(features)&{'Risk_Label','Overlap_Acres','Historical_P33_Acres','Historical_P67_Acres','Record_ID','Year'}
        restored=joblib.load(directory/artifact)
        processor=joblib.load(directory/preprocessing)
        assert list(restored.feature_names_in_)==features
        assert restored.predict(row[features]).shape==(1,)
        assert np.array_equal(processor.transform(row[features]),restored.named_steps['preprocessing'].transform(row[features]))
