"""Disclosure controls are separate from concentration/risk calculations."""
from copy import deepcopy

NUMERIC_AGGREGATES = {
    'crop_share_of_regional_window_acreage',
    'plan_count', 'farmer_count', 'planned_acreage', 'total_acreage',
    'overlapping_farmer_count', 'overlapping_plan_count', 'total_planned_acreage',
    'harvest_overlap_intensity', 'scenario_inclusive_acreage', 'scenario_inclusive_farmer_count',
    'peak_plan_centered_29_day_planned_acreage', 'peak_window_plan_count', 'peak_window_acreage_share',
    'estimated_production_kg', 'historical_concentration_baseline',
}


def farmer_view(value):
    """Do not release exact collective numbers, even above the minimum cohort size.

    Stateless minimum-size controls cannot safely release editable-owner totals.
    Preserve decision/evidence fields; never apply to the owner's individual plan.
    """
    if isinstance(value, list):
        return [farmer_view(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: farmer_view(item) for key, item in value.items()
              if key not in NUMERIC_AGGREGATES | {'cluster_context','kmeans','dbscan','noise','baseline','effective_k'}}
    result['privacy_policy'] = 'collective_numeric_values_withheld_from_farmer'
    return result


def analyst_view(value):
    """Suppress complementary cluster partitions if any partition is suppressed."""
    result = deepcopy(value)
    # Cross-algorithm and baseline totals must not reconstruct a hidden partition.
    hidden = (result.get('noise', {}).get('status') == 'suppressed' or
              any(group.get('status') == 'suppressed'
                  for name in ('kmeans','dbscan','baseline') for group in result.get(name, [])))
    if hidden:
        for name in ('kmeans','dbscan','baseline'):
            result[name] = [dict(status='suppressed', reason='Complementary partition suppression')]
        result['noise'] = dict(status='suppressed', meaning='Noise is not a risk label')
    for key in ('kmeans', 'dbscan', 'baseline'):
        groups = result.get(key, [])
        noise_private = key == 'dbscan' and result.get('noise', {}).get('status') == 'suppressed'
        if noise_private or any(group.get('status') == 'suppressed' for group in groups):
            result[key] = [dict(status='suppressed', reason='Complementary partition suppression')]
            if key == 'dbscan':
                result['noise'] = dict(status='suppressed', meaning='Noise is not a risk label')
    result['privacy_policy'] = 'minimum_three_distinct_farmers_and_complementary_partitions'
    return result
