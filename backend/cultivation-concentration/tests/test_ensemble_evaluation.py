"""Regression tests for probability alignment and frozen decision semantics."""
import numpy as np
import pandas as pd
import pytest
from ml.ensemble_decisions import combine,error_overlap
from ml.training.evaluate_xgboost_catboost_ensemble import probabilities,best


def test_reordered_classes_are_aligned_before_combining():
    class Fixture:
        classes_ = np.array([2,0,1])
        def predict_proba(self, inputs):
            return np.array([[.6,.3,.1]])
    aligned, metadata = probabilities(Fixture(),pd.DataFrame({'acres':[1]}),['acres'])
    np.testing.assert_array_equal(aligned,[[.3,.1,.6]])
    assert metadata['aligned_labels']==['Low','Medium','High']
    assert combine(aligned,aligned,dict(method='average',xgboost_weight=.5)).tolist()==['High']


def test_shared_wrong_prediction_cannot_be_fixed_by_convex_average():
    x=np.array([[.1,.2,.7],[.2,.6,.2]])
    c=np.array([[.3,.1,.6],[.6,.3,.1]])
    overlap=error_overlap(['Medium','Medium'],x,c)
    assert overlap['both_wrong_same_prediction']==1
    assert overlap['only_xgboost_correct']==1
    assert overlap['convex_average_optimistic_ceiling']==.5
    for weight in [0,.25,.5,.75,1]:
        assert combine(x,c,dict(method='average',xgboost_weight=weight))[0]=='High'
    assert combine(x,c,dict(method='disagreement',rule='prefer_medium')).tolist()==['High','Medium']


def test_probability_shape_values_and_weights_are_checked():
    valid=np.array([[.2,.3,.5]])
    for invalid in [np.array([[.2,.3]]),np.array([[.2,np.nan,.8]]),np.array([[.2,.3,.4]])]:
        with pytest.raises(ValueError):combine(valid,invalid,dict(method='average',xgboost_weight=.5))
    with pytest.raises(ValueError):combine(valid,valid,dict(method='average',xgboost_weight=2))


def test_selection_ignores_final_year_metrics():
    def result(f1):
        fold=dict(accuracy=.9)
        return dict(pooled=dict(accuracy=.9,macro_f1=f1,per_class={'Medium':{'recall':.5}}),
                    folds={'2023':fold,'2024':fold})
    results={'a':result(.8),'b':result(.7)}
    results['b']['folds']['2025']=dict(accuracy=1.)
    results['a']['folds']['2025']=dict(accuracy=0.)
    assert best(results,results,results['a'])=='a'
