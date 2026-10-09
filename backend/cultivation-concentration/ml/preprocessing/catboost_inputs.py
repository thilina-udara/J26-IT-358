"""Named CatBoost inputs without externally fitted target/category encodings."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin


class CatBoostInputs(TransformerMixin, BaseEstimator):
    def __init__(self, features, categorical):
        self.features = features
        self.categorical = categorical

    def fit(self, X, y=None):
        self.feature_names_in_ = np.array(self.features)
        self.transform(X)
        return self

    def transform(self, X):
        result = X.loc[:, self.features].copy()
        for column in self.features:
            if column in self.categorical:
                result[column] = result[column].fillna('__MISSING__').astype(str)
            else:
                result[column] = result[column].astype(float)
                if np.isinf(result[column]).any():
                    raise ValueError('Infinite CatBoost numeric input')
        return result

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_
