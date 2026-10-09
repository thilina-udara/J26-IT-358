"""Availability gates tested with a recording stub; no models are trained."""
from datetime import datetime, timezone
from app.services.historical_prediction import HistoricalPredictor, predict_context


class RecordingModel:
    def predict(self, frame):
        self.frame = frame
        return [1]


def test_historical_availability_district_and_future_exclusion():
    cutoff = datetime(2022, 6, 1, tzinfo=timezone.utc)
    row = dict(district="Matara", crop="Corn", season="Maha", year=2021,
        land_acres=10, production_kg=100, provenance_verified=True,
        evidence_reference="fictional-source", available_at=cutoff)
    model = RecordingModel()
    predictor = HistoricalPredictor(model, [row, dict(row, year=2022, land_acres=1e9)],
        "fictional-model", cutoff, 2021, 2021)
    result = predictor.predict("Matara", "Corn", "Maha", 2022, cutoff)
    assert result["risk_level"] == "Medium"
    assert model.frame.iloc[0]["Historical_Mean_Land_Acres"] == 10
    assert predictor.predict("Hambantota", "Corn", "Maha", 2022, cutoff)["risk_level"] is None
    row["provenance_verified"] = False
    assert predictor.predict("Matara", "Corn", "Maha", 2022, cutoff)["risk_level"] is None


def test_unconfigured_model_and_missing_statistical_year_mapping_fail_closed():
    cutoff = datetime(2022, 6, 1, tzinfo=timezone.utc)
    assert predict_context(None, {}, "Maha", cutoff)["risk_level"] is None
    predictor = HistoricalPredictor(RecordingModel(), [], "fictional-model", cutoff, 2021, 2021)
    assert predict_context(predictor, {}, "Maha", cutoff)["risk_level"] is None
