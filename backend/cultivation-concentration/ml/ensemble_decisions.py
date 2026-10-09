"""Frozen decisions over aligned [Low, Medium, High] probabilities."""
import numpy as np

LABELS = np.array(['Low', 'Medium', 'High'])


def validate(probabilities):
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError('Expected finite normalized three-class probabilities')
    return p


def combine(xgboost, catboost, specification):
    x, c = validate(xgboost), validate(catboost)
    if x.shape != c.shape:
        raise ValueError('Probability cohorts must match')
    xp, cp = x.argmax(axis=1), c.argmax(axis=1)
    if specification['method'] == 'average':
        weight = specification['xgboost_weight']
        if not 0 <= weight <= 1:
            raise ValueError('Convex weight required')
        result = (weight*x+(1-weight)*c).argmax(axis=1)
    elif specification['method'] == 'disagreement':
        rule = specification['rule']
        if rule == 'prefer_xgboost':
            result = xp
        elif rule == 'prefer_catboost':
            result = cp
        elif rule == 'higher_confidence':
            result = np.where(c.max(axis=1) > x.max(axis=1), cp, xp)
        elif rule == 'prefer_medium':
            result = np.where((xp != cp) & ((xp == 1) | (cp == 1)), 1, xp)
        else:
            raise ValueError('Unsupported frozen disagreement rule')
    else:
        raise ValueError('Unsupported ensemble method')
    return LABELS[result]


def error_overlap(actual, xgboost, catboost):
    actual = np.asarray(actual)
    xp, cp = LABELS[validate(xgboost).argmax(axis=1)], LABELS[validate(catboost).argmax(axis=1)]
    x, c = xp == actual, cp == actual
    return dict(records=len(actual), both_correct=int((x&c).sum()), only_xgboost_correct=int((x&~c).sum()),
        only_catboost_correct=int((~x&c).sum()), both_wrong=int((~x&~c).sum()),
        both_wrong_same_prediction=int((~x&~c&(xp==cp)).sum()),
        both_wrong_different_predictions=int((~x&~c&(xp!=cp)).sum()),
        either_prediction_correct_oracle_accuracy=float((x|c).mean()),
        convex_average_optimistic_ceiling=float(1-(~x&~c&(xp==cp)).mean()))
