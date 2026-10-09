"""Regression checks for native categorical handling and fold restrictions."""
import joblib
import numpy as np
import pandas as pd
import pytest
from catboost import CatBoostClassifier
from sklearn.pipeline import Pipeline
from ml.preprocessing.catboost_inputs import CatBoostInputs
from ml.training.compare_catboost import cohort


def test_native_missing_categories_unseen_values_and_reload(tmp_path):
    training = pd.DataFrame({'district':['Matara', 'Hambantota', None]*4,
                             'acres':[1., 2., np.nan]*4})
    model = Pipeline([('inputs', CatBoostInputs(['district','acres'], ['district'])),
        ('classifier', CatBoostClassifier(iterations=8, depth=2, loss_function='MultiClass',
            cat_features=['district'], random_seed=42, thread_count=1, verbose=False, allow_writing_files=False))])
    model.fit(training, [0,1,2]*4)
    proposed = pd.DataFrame({'district':['unseen',None], 'acres':[8.,np.nan]})
    original = proposed.copy(deep=True)
    predicted = model.predict_proba(proposed)
    pd.testing.assert_frame_equal(proposed, original)
    assert predicted.shape == (2,3) and np.isfinite(predicted).all()
    joblib.dump(model, tmp_path/'model.joblib')
    np.testing.assert_array_equal(joblib.load(tmp_path/'model.joblib').predict_proba(proposed), predicted)


def test_cohort_rejects_cutoff_overlap_and_excludes_insufficient_evidence():
    data = pd.DataFrame({'Record_ID':['a','b','c'], 'Year':[2022,2023,2023],
        'Risk_Label':['Low','Medium','insufficient_evidence'],
        'Prediction_Cutoff':pd.to_datetime(['2022-01-01','2023-01-01','2023-01-01'])})
    train, test = cohort(data, 2023)
    assert train.Record_ID.tolist() == ['a'] and test.Record_ID.tolist() == ['b']
    data.loc[0,'Prediction_Cutoff'] = pd.Timestamp('2023-01-01')
    with pytest.raises(AssertionError):
        cohort(data, 2023)
