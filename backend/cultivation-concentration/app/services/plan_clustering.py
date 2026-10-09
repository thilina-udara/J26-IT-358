"""Descriptive clustering of available, active, pre-planting plans."""
import json
from datetime import date, datetime, timezone, timedelta
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MIN_FARMERS = 3  # Disclosure policy, not a risk threshold.


def snapshot_versions(repository, cutoff, connection=None):
    """Existing snapshot policy plus version lineage, optionally in caller transaction."""
    if connection is None:
        with repository.connection() as db:
            db.execute('BEGIN')
            return snapshot_versions(repository, cutoff, db)
    rows = connection.execute('SELECT version_id,recorded_at,payload FROM cultivation_plan_versions ORDER BY version_id').fetchall()
    latest = {}
    for row in rows:
        recorded = datetime.fromisoformat(row['recorded_at'])
        if recorded <= cutoff:
            plan = json.loads(row['payload'])
            submitted = datetime.fromisoformat(plan['submitted_at'])
            if submitted <= cutoff:
                latest[plan['plan_id']] = dict(plan=plan, version_id=row['version_id'], recorded_at=row['recorded_at'])
    return [entry for entry in latest.values() if entry['plan']['status']=='active'
            and date.fromisoformat(entry['plan']['planting_date']) > cutoff.date()
            and date.fromisoformat(entry['plan']['expected_harvest_date']) > cutoff.date()]


def snapshot(repository, cutoff):
    return [entry['plan'] for entry in snapshot_versions(repository, cutoff)]


def summarize(plans):
    farmers = len({p['farmer_id'] for p in plans})
    if farmers < MIN_FARMERS:
        return {'status':'suppressed', 'reason':'Fewer than three distinct farmers; cluster details withheld.'}
    dates = [date.fromisoformat(p['expected_harvest_date']) for p in plans]
    windows = [[p for p,d in zip(plans,dates) if center-timedelta(days=14)<=d<=center+timedelta(days=14)] for center in dates]
    peak = max(windows,key=lambda window:sum(p['land_size_acres'] for p in window))
    result = dict(status='available', plan_count=len(plans), farmer_count=farmers,
                planned_acreage=float(sum(p['land_size_acres'] for p in plans)),
                crops=sorted({p['crop'] for p in plans}), regions=sorted({p['region'] for p in plans}),
                harvest_period_start=min(dates).isoformat(),harvest_period_end=max(dates).isoformat())
    if len({p['farmer_id'] for p in peak}) >= MIN_FARMERS:
        result.update(peak_plan_centered_29_day_planned_acreage=float(sum(p['land_size_acres'] for p in peak)),
                      peak_window_plan_count=len(peak),
                      peak_window_acreage_share=float(sum(p['land_size_acres'] for p in peak)/sum(p['land_size_acres'] for p in plans)))
    else:
        result['peak_window_status']='suppressed: fewer than three distinct farmers'
    return result


def analyze(plans, district, clusters=3, eps=1.0, min_samples=3):
    plans = sorted([p for p in plans if p['district']==district], key=lambda p:p['plan_id'])
    response = dict(district=district, coverage_warning='Submitted intentions only; unverified participation and harvest estimates. Aggregate disclosure control is not differential privacy.',
                    interpretation='Clusters describe plan similarity and density, not oversupply or Low/Medium/High risk.',
                    baseline=[], kmeans=[], dbscan=[], noise={})
    if len(plans)<3 or len({p['farmer_id'] for p in plans})<MIN_FARMERS:
        response['status']='insufficient_or_private'
        return response
    # Two categorical blocks of equal weight; standardize numeric dimensions.
    # Harvest offset is elapsed calendar days, not an ordinal crop/region code.
    dates=[date.fromisoformat(p['expected_harvest_date']) for p in plans]
    numeric=np.array([[np.log1p(p['land_size_acres']), (d-min(dates)).days] for p,d in zip(plans,dates)])
    encoder=OneHotEncoder(sparse_output=False,handle_unknown='ignore')
    encoded=encoder.fit_transform([[p['crop'],p['region']] for p in plans])/np.sqrt(2)
    x=np.column_stack([encoded,StandardScaler().fit_transform(numeric)])
    unique=len(np.unique(x,axis=0)); k=min(clusters,unique,len(plans))
    km=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(x)
    density=DBSCAN(eps=eps,min_samples=min_samples).fit_predict(x)
    for name,labels in [('kmeans',km),('dbscan',density)]:
        for label in sorted(set(labels)-{-1}):
            summary=summarize([p for p,l in zip(plans,labels) if l==label])
            summary.update(cluster_id=int(label),meaning='Similar crop/region, log-acreage and harvest timing' if name=='kmeans' else 'Connected dense neighborhood in encoded/scaled plan space')
            response[name].append(summary)
    noise_plans=[p for p,l in zip(plans,density) if l==-1]
    response['noise']=summarize(noise_plans) if noise_plans else {'status':'empty'}
    response['noise']['meaning']='Sparse/unusual in this metric; review candidate, not automatically erroneous or high-risk.'
    # Same exact grouping and inclusive +/-14-day rule as Phase 1, without IDs.
    for crop,region in sorted({(p['crop'],p['region']) for p in plans}):
        group=[p for p in plans if (p['crop'],p['region'])==(crop,region)]
        response['baseline'].append(summarize(group))
    response.update(status='available', effective_k=k,
                    configuration=dict(requested_k=clusters,eps=eps,min_samples=min_samples,random_state=42),
                    feature_definition='One-hot crop/region weighted 1/sqrt(2); standardized log1p acreage and elapsed harvest days; district analyzed separately')
    return response
