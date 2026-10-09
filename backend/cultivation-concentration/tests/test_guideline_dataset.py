import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'data/guidelines/v1'


def test_guideline_structure_provenance_and_inactive_status():
    schema=json.loads((ROOT/'guideline.schema.json').read_text(encoding='utf-8'))
    seen=set();crops=set()
    for name,statuses in [('verified_entries.json',{'source_checked'}),('unverified_entries.json',{'unverified','conflicting_or_ambiguous'})]:
        records=json.loads((ROOT/name).read_text(encoding='utf-8'))['entries']
        for r in records:
            assert set(r)==set(schema['properties'])
            assert r['verification_status'] in statuses
            assert r['entry_id'] not in seen
            seen.add(r['entry_id']);crops.add(r['crop_name'])
            assert r['planning_activation'] is False and r['quantity'] is None
            assert r['publication_date'] is None and r['historical_available_at'] is None
            for field in ('days_offset','rate_per_hectare','quantity'):
                if r[field] is not None:assert r[field]['min']<=r[field]['max']
            if r['verification_status']=='source_checked':
                assert r['source_url'].startswith('https://doa.gov.lk/') and r['checked_on']=='2026-10-08'
    assert crops=={'Bandakka','Brinjal','Pumpkin','Corn','Mung Beans','Chillies'}


def test_anchors_and_unresolved_claims():
    checked=json.loads((ROOT/'verified_entries.json').read_text())['entries']
    pending=json.loads((ROOT/'unverified_entries.json').read_text())['entries']
    assert any(r['crop_name']=='Brinjal' and r['timing_reference']=='transplanting' for r in checked)
    assert any(r['crop_name']=='Pumpkin' and r['timing_reference']=='flowering' for r in checked)
    assert not any(r['crop_name']=='Pumpkin' and r['guideline_category']=='fertilizer' for r in checked)
    assert len([r for r in pending if r['source_type']=='missing_draft'])==6
    assert any(r['repeat_interval_days']==2 for r in checked if r['crop_name']=='Bandakka')


def test_received_drafts_remain_unverified_and_traceable():
    folder=ROOT.parent/'v1.1'
    claims=json.loads((folder/'draft_claims.json').read_text(encoding='utf-8'))['claims']
    assert len(claims)==110
    assert len({c['crop_name'] for c in claims})==6
    lines=(folder/'user_drafts.txt').read_text(encoding='utf-8').splitlines()
    for claim in claims:
        assert claim['claim']==lines[claim['draft_line']-1].strip()
        assert claim['status']=='unverified_user_draft' and claim['planning_activation'] is False
    records=json.loads((folder/'unverified_entries.json').read_text(encoding='utf-8'))['entries']
    assert not any(r['source_type']=='missing_draft' for r in records)
    assert all(r['planning_activation'] is False for r in records)
