import csv
import pytest
from ml.asc_2025_actual_evaluation import evaluate_file,load_authorized
from tests.test_production_reference import row


def test_authorized_year_routing_and_determinism(tmp_path):
    source=tmp_path/'fictional.csv'
    rows=[row('history'),row('permitted',Year='2025',Planting_Date='1/1/2025',Expected_Harvest_Date='4/1/2025'),
          dict(Year='2024'),dict(Year='2026')]
    with source.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(row('x')));writer.writeheader();writer.writerows(rows)
    with pytest.raises(PermissionError):load_authorized(source)
    result=evaluate_file(source,authorize_2025=True)
    assert result['summary']==dict(total=1,Low=0,Medium=0,High=0,insufficient_evidence=1)
    assert result['excluded_rows_routed_by_year_only']==2
    assert result['reference']['permitted_years']==[2020,2021,2022,2023]
    assert all(w['recorded_year']<=2023 for w in result['reference']['windows'])
    assert result==evaluate_file(source,authorize_2025=True)


def test_protected_history_rejected_before_measurements():
    from ml.asc_2025_backtest import replay
    with pytest.raises(ValueError):replay([dict(Year='2024')],[],access_authorized=True,reference_end_year=2023)
