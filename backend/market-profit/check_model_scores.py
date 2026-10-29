import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

LABELS = ("Low", "Medium", "High")
FILES = {
    "demand": ("demand_test_predictions_export.csv", "market-demand-training"),
    "price": ("price_test_predictions_export.csv", "price_forecasting"),
    "risk": ("profit_risk_test_predictions_export.csv", "profit-risk-training"),
}


def locate(root, kind, explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"File not found: {path}")
        return path
    filename, folder = FILES[kind]
    # Prefer the active component's canonical models directory over backups.
    for path in (root / folder / "models" / filename, root / filename):
        if path.is_file():
            return path.resolve()
    matches = sorted(p.resolve() for p in root.rglob(filename) if p.is_file())
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            f"{filename} was not found under {root}. "
            "Use --data-dir for the correct folder, or --" + kind + " for its exact path."
        )
    raise ValueError(
        f"Multiple copies of {filename} found. Use --{kind} to select the correct file:\n"
        + "\n".join(str(p) for p in matches)
    )


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"{path.name}: missing CSV header.")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"{path.name}: duplicate column names.")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: no test rows.")
    return rows


def require_columns(rows, names, title):
    missing = sorted(set(names) - set(rows[0]))
    if missing:
        raise ValueError(f"{title}: missing columns: {', '.join(missing)}")


def classification(rows, actual, predicted):
    require_columns(rows, [actual, predicted], "Classification export")
    matrix = [[0] * 3 for _ in LABELS]
    for number, row in enumerate(rows, 2):
        if not isinstance(row[actual], str) or not isinstance(row[predicted], str):
            raise ValueError(f"CSV row {number}: a classification label is missing.")
        a, p = row[actual].strip(), row[predicted].strip()
        if a not in LABELS or p not in LABELS:
            raise ValueError(f"CSV row {number}: unexpected label {a!r} or {p!r}.")
        matrix[LABELS.index(a)][LABELS.index(p)] += 1
    counts = [sum(row) for row in matrix]
    class_metrics = {}
    for i, name in enumerate(LABELS):
        tp = matrix[i][i]
        predicted_count = sum(matrix[j][i] for j in range(3))
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / counts[i] if counts[i] else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        class_metrics[name] = {"precision": precision, "recall": recall,
                               "f1": f1, "support": counts[i]}
    n = len(rows)
    correct = sum(matrix[i][i] for i in range(3))
    return {
        "rows": n, "correct": correct, "accuracy_pct": 100 * correct / n,
        "macro_f1": sum(v["f1"] for v in class_metrics.values()) / 3,
        "high_recall_pct": class_metrics["High"]["recall"] * 100,
        "high_correct_count": matrix[2][2], "high_actual_count": counts[2],
        "class_counts": dict(zip(LABELS, counts)),
        "evaluation_largest_class_share_pct": 100 * max(counts) / n,
        "confusion_matrix": matrix, "per_class": class_metrics,
    }


def regression(rows, actual, predicted):
    require_columns(rows, [actual, predicted], "Regression export")
    values, errors, percentage_errors = [], [], []
    for number, row in enumerate(rows, 2):
        try:
            a, p = float(row[actual]), float(row[predicted])
        except (TypeError, ValueError):
            raise ValueError(f"CSV row {number}: actual/predicted value is not numeric.") from None
        if not (math.isfinite(a) and math.isfinite(p)) or a < 0 or p < 0:
            raise ValueError(f"CSV row {number}: price/quantity must be finite and nonnegative.")
        values.append(a)
        errors.append(p - a)
        if a > 0:
            percentage_errors.append(abs(p - a) / a)
    n = len(rows)
    squared_error = math.fsum(e * e for e in errors)
    mean_actual = math.fsum(values) / n
    total_variance = math.fsum((a - mean_actual) ** 2 for a in values)
    return {
        "rows": n,
        "mae": math.fsum(abs(e) for e in errors) / n,
        "rmse": math.sqrt(squared_error / n),
        "mape_pct": 100 * math.fsum(percentage_errors) / len(percentage_errors)
                    if percentage_errors else None,
        "within_10pct_rate_pct":
            100 * sum(e <= 0.1 + 1e-12 for e in percentage_errors) / len(percentage_errors)
            if percentage_errors else None,
        "percentage_metric_rows": len(percentage_errors),
        "zero_actual_rows": n - len(percentage_errors),
        "r2": 1 - squared_error / total_variance if n > 1 and total_variance > 0 else None,
    }


def price_checks(rows):
    require_columns(rows, ["horizon", "forecast_date", "latest_observation_date",
                          "training_cutoff", "target_date"], "Price export")
    checks = {
        "training_cutoff_after_latest_observation": 0,
        "observation_less_than_one_week_before_forecast": 0,
        "target_not_after_forecast": 0,
        "target_forecast_gap_differs_from_horizon": 0,
    }
    groups = {}
    for number, row in enumerate(rows, 2):
        try:
            horizon = float(row["horizon"])
            if not math.isfinite(horizon) or not horizon.is_integer() or not 1 <= horizon <= 16:
                raise ValueError
            h = int(horizon)
            fc, obs, cutoff, target = (
                date.fromisoformat(row[c]) for c in
                ["forecast_date", "latest_observation_date", "training_cutoff", "target_date"]
            )
        except (TypeError, ValueError):
            raise ValueError(f"Price CSV row {number}: invalid horizon or ISO date.") from None
        groups.setdefault(h, []).append(row)
        checks["training_cutoff_after_latest_observation"] += int(cutoff > obs)
        checks["observation_less_than_one_week_before_forecast"] += int(obs > fc - timedelta(days=7))
        checks["target_not_after_forecast"] += int(target <= fc)
        checks["target_forecast_gap_differs_from_horizon"] += int((target - fc).days != h * 7)
    return checks, groups


def calculate(paths):
    demand, price, risk = (read_rows(paths[k]) for k in ["demand", "price", "risk"])
    checks, horizons = price_checks(price)
    primary = [row for h, rows in horizons.items() if h >= 8 for row in rows]
    result = {
        "method": "Recalculation from saved test predictions; no model inference or retraining",
        "input_files": {k: str(v) for k, v in paths.items()},
        "demand_classification": classification(demand, "actual_demand_level", "predicted_demand_level"),
        "demand_quantity": regression(demand, "actual_sales_quantity_kg", "predicted_sales_quantity_kg"),
        "price_overall_1_16_weeks": regression(price, "actual_price", "predicted_price"),
        "price_primary_8_16_weeks": regression(primary, "actual_price", "predicted_price") if primary else None,
        "price_csv_timing_checks": checks,
        "price_by_horizon": {h: regression(rows, "actual_price", "predicted_price")
                             for h, rows in sorted(horizons.items())},
        "profit_risk_classifier_benchmark": classification(risk, "actual_risk_class", "predicted_risk_class"),
        "profit_risk_record_origins": dict(Counter(row.get("record_origin", "Unspecified") for row in risk)),
    }
    return result


def fmt(value, digits=2):
    return f"{value:.{digits}f}" if value is not None else "undefined"


def print_results(result, per_horizon=False):
    print("AgriSense evaluation scores")
    print("Mode: saved test-prediction CSV check; no model inference or retraining.")
    for kind, path in result["input_files"].items():
        print(f"  {kind}: {path}")
    d = result["demand_classification"]
    q = result["demand_quantity"]
    print(f"\nDemand category: {d['accuracy_pct']:.2f}% accuracy "
          f"({d['correct']}/{d['rows']} correct), macro-F1 {d['macro_f1']:.4f}")
    print(f"Demand quantity: MAPE {fmt(q['mape_pct'])}%, MAE {q['mae']:.2f} kg, "
          f"RMSE {q['rmse']:.2f} kg, R2 {fmt(q['r2'], 4)}")
    for key, label in [("price_overall_1_16_weeks", "Price, available 1-16-week horizons"),
                       ("price_primary_8_16_weeks", "Price, available 8-16-week horizons")]:
        p = result[key]
        if p:
            print(f"\n{label}: {p['rows']:,} forecast rows")
            print(f"  MAPE {fmt(p['mape_pct'])}%, MAE {p['mae']:.2f} LKR/kg, "
                  f"RMSE {p['rmse']:.2f} LKR/kg")
            print(f"  Within +/-10%: {fmt(p['within_10pct_rate_pct'])}%; R2 {fmt(p['r2'], 4)}")
            if p["zero_actual_rows"]:
                print(f"  Percentage metrics exclude {p['zero_actual_rows']} zero actual values.")
    missing = sorted(set(range(1, 17)) - set(result["price_by_horizon"]))
    print("\nPrice horizons present:", ", ".join(map(str, result["price_by_horizon"])))
    if missing:
        print("Missing horizons (not evaluated):", ", ".join(map(str, missing)))
    print("CSV timing violations:", result["price_csv_timing_checks"])
    print("These date-column checks do not independently verify feature construction.")
    r = result["profit_risk_classifier_benchmark"]
    print(f"\nProfit-risk ML benchmark: {r['accuracy_pct']:.2f}% accuracy "
          f"({r['correct']}/{r['rows']} correct), macro-F1 {r['macro_f1']:.4f}")
    print(f"  High-risk recall: {r['high_recall_pct']:.2f}% "
          f"({r['high_correct_count']}/{r['high_actual_count']} detected)")
    print("  Actual class counts:", r["class_counts"])
    print("  Record origins:", result["profit_risk_record_origins"])
    print("  Confusion matrix: rows=actual; columns=predicted; order=Low, Medium, High")
    for name, row in zip(LABELS, r["confusion_matrix"]):
        print(f"    {name}: {row}")
    print("  This classifier benchmark is separate from the live profit-risk rule engine.")
    if per_horizon:
        print("\nPrice results by horizon (weeks):")
        for horizon, p in result["price_by_horizon"].items():
            print(f"  {horizon:2d}: n={p['rows']:,}, MAPE={fmt(p['mape_pct'])}%, "
                  f"MAE={p['mae']:.2f} LKR/kg, within +/-10%={fmt(p['within_10pct_rate_pct'])}%")
    print("\nMAPE is an error measure. Do not label 100 - MAPE as classification accuracy.")


def main():
    script_dir = Path(__file__).resolve().parent
    default_root = script_dir / "ml" if (script_dir / "ml").is_dir() else script_dir
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=default_root,
                        help="Folder containing the exports, or your component's ml folder.")
    for kind in FILES:
        parser.add_argument("--" + kind, type=Path, help=f"Exact {kind} prediction CSV path.")
    parser.add_argument("--per-horizon", action="store_true", help="Print a row for each price horizon.")
    parser.add_argument("--output-json", type=Path, help="Optionally save the calculated metrics as JSON.")
    args = parser.parse_args()
    try:
        root = args.data_dir.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Data folder not found: {root}")
        paths = {kind: locate(root, kind, getattr(args, kind)) for kind in FILES}
        result = calculate(paths)
        if args.output_json:
            output = args.output_json.expanduser().resolve()
            # Create a new result file; never overwrite a dataset or previous result.
            with output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, allow_nan=False)
        print_results(result, args.per_horizon)
        if args.output_json:
            print("JSON saved:", args.output_json.resolve())
    except (OSError, ValueError, csv.Error, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
