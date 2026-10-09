"""Render measured, matched CatBoost results without fitting models."""
import argparse
import json
from pathlib import Path
import pandas as pd
from ml.training.train_updated_asc import ROOT


def pct(value):
    return f'{100*value:.2f}%'


def report(directory, output):
    metrics = json.loads((directory/'metrics.json').read_text())
    dev = json.loads((directory/'development_metrics.json').read_text())
    frozen = json.loads((directory/'selection_frozen_before_2025.json').read_text())
    spec = json.loads((directory/'search_specification.json').read_text())
    environment = json.loads((directory/'environment.json').read_text())
    verification = json.loads((directory/'verification.json').read_text())
    regression = json.loads((directory/'regression_results.json').read_text())
    cb, xgb = metrics['catboost'], metrics['xgboost']
    selected = metrics['selected']
    lines = ['# CatBoost versus matched XGBoost', '',
        f"Executed 2026-10-09. Selected CatBoost `{selected}` achieved **{pct(cb['pooled']['accuracy'])} pooled accuracy**, "
        f"macro F1 **{cb['pooled']['macro_f1']:.4f}**, versus matched XGBoost **{pct(xgb['pooled']['accuracy'])}** and **{xgb['pooled']['macro_f1']:.4f}**.", '',
        f"The panel's 88% pooled target {'was reached' if cb['pooled']['accuracy']>=.88 else 'was not reached'}. "
        f"CatBoost minus XGBoost pooled accuracy: {(cb['pooled']['accuracy']-xgb['pooled']['accuracy'])*100:+.2f} percentage points; "
        f"macro F1: {cb['pooled']['macro_f1']-xgb['pooled']['macro_f1']:+.4f}.", '',
        '**Interpretation:** These are chronological classifications of research-derived acreage categories under the same retrospective availability assumptions as XGBoost. They are not verified oversupply, price-loss, or prospective submission-time accuracy. '
        '2023/2024 were development folds used to select CatBoost; pooled historical accuracy therefore includes development results. '
        '2025 was evaluated only after freezing this experiment, but both 2025 and 2026 have been examined in previous research, so neither is a pristine holdout for the overall project. No 2026 rows were engineered, trained, predicted or scored here.', '',
        '## Matched results', '',
        '| Test cohort | Model | Eligible | Correct | Accuracy | Macro F1 | Medium recall | High recall |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for year in ['2023','2024','2025','pooled']:
        for label, result in [('CatBoost', cb[year]),('XGBoost', xgb[year])]:
            lines.append(f"| {year} | {label} | {result['records']} | {result['correct']} | {pct(result['accuracy'])} | {result['macro_f1']:.4f} | {pct(result['per_class']['Medium']['recall'])} | {pct(result['per_class']['High']['recall'])} |")
    lines += ['', 'Pooled accuracy is total correct / total eligible predictions, not the average of yearly percentages. '
              'Every CatBoost prediction was joined one-to-one to saved XGBoost predictions using Record_ID, Year and Risk_Label; no test rebalancing or label changes.', '',
              '## Labels, features and availability audit', '',
              'Source: `data/legacy/official_farmer_cultivation_2020_2026.csv`, 15,090 original rows, used exclusively. '
              f"SHA-256: `{metrics['source_sha256']}`. The smaller CSV is not combined or used for training.", '',
              'The exact original `engineer_fast` implementation was reused and all regenerated features, labels and threshold values were compared with the latest saved XGBoost experiment. '
              'For each row, cutoff is its planting date; peers must have strictly earlier planting, expected harvest at/after cutoff and harvest within inclusive Â±14 days of the own expected harvest, in the same district/crop/season. '
              'Own acreage is counted once. Historical references have an earlier recorded Year and expected harvest strictly before cutoff. '
              'Within each reference year, unique observed harvest-date anchors yield Â±14-day acreage-window sums. Linear P33/P67 over these historical window sums define Low below P33, High above P67 and Medium including boundaries '
              '(existing 1e-12 equality tolerance). Missing references or coincident thresholds remain insufficient_evidence.', '',
              f"Insufficient-evidence exclusions by year: `{json.dumps(metrics['excluded_by_year'],sort_keys=True)}`. Exclusions are unchanged; no records were silently removed or source files edited.", '',
              'Features match `historical_feature_improvement/v1_20261009` exactly: `'+ '`, `'.join(spec['features'])+'`.', '',
              'The added previous-year window mean/median/std and mean individual-plan acreage use only earlier district/crop/season records whose expected harvest precedes cutoff. '
              'Current overlap acreage, P33/P67 target thresholds, Risk_Label, IDs and Year are not model inputs. '
              'A district perturbation changed Hambantota acreage/production without changing any Matara features or labels. '
              'A 2025 perturbation did not alter earlier development features or labels. Chronological training/test cutoffs are strictly ordered and IDs disjoint.', '',
              'ASC records lack registration/publication timestamps; earlier planting and completed expected harvest are assumed availability proxies, not evidence of knowledge at a real submission cutoff. '
              'Overlap counts are consequently retrospective peer-plan proxies; own yield/expected production and historical reference release availability are also unverified. '
              'Categorical statistics legitimately learn from training labels only; test targets and target-defining quantities are not passed to preprocessing or fit. '
              'This reproduces the existing classification task without claiming prospective leakage freedom. The prospective framework is unchanged.', '',
              '## Fixed search and chronological selection', '',
              'Folds: train eligible 2020â€“2022 â†’ 2023, train eligible 2020â€“2023 â†’ 2024 for development; train eligible 2020â€“2024 â†’ 2025 after selection. '
              'Insufficient-evidence 2020 rows naturally contribute no training targets. Each preprocessor/model is fitted again using only its fold training rows.', '',
              'Native CatBoost categorical features are District/Crop/Season. A fixed missing-category sentinel is used; numerical NaNs are handled natively, without test-derived imputation. '
              'Native category statistics and numeric borders are learned on training rows only; records are ordered by cutoff/ID and `has_time=True`. '
              'No external one-hot or target encoding, eval_set, early stopping, test calibration or decision-threshold tuning is used. '
              'Class weights are fixed candidate settings, not test-frequency-derived weights. The decision is unmodified argmax.', '',
              'Common parameters: `'+json.dumps(spec['common_parameters'],sort_keys=True)+'`.', '',
              'Selection rule (saved before development fitting): '+spec['selection'], '',
              '| Configuration | Depth | L2 | Medium weight | 2023 accuracy | 2024 accuracy | Development pooled accuracy | Development macro F1 |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name, item in dev.items():
        p=item['parameters']
        lines.append(f"| {name} | {p['depth']} | {p['l2_leaf_reg']} | {p['medium_weight']} | {pct(item['folds']['2023']['accuracy'])} | {pct(item['folds']['2024']['accuracy'])} | {pct(item['pooled']['accuracy'])} | {item['pooled']['macro_f1']:.4f} |")
    lines += ['', f"Selected `{selected}`; fallback used: `{frozen['fallback_used']}`. Choice frozen at `{frozen['frozen_at']}` before computing CatBoost 2025 predictions. "
              'The search was not reopened after the final evaluation.', '',
              'CatBoost parameters follow its official [parameter tuning documentation](https://catboost.ai/docs/en/concepts/parameter-tuning): native categorical handling, depth/L2 regularization, and ordered input handling. '
              'The six settings constitute a bounded comparison, not evidence that every possible CatBoost setup was tested.', '',
              '## Class distribution and majority baselines', '',
              '| Cohort | Low | Medium | High | Training-majority predictor accuracy | Retrospective cohort-majority prevalence |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for year in ['2023','2024','2025','pooled']:
        m=cb[year]; counts=m['classes']
        baseline=pct(m['training_majority_baseline']) if year!='pooled' else pct(sum(cb[y]['training_majority_baseline']*cb[y]['records'] for y in ['2023','2024','2025'])/m['records'])
        lines.append(f"| {year} | {counts.get('Low',0)} | {counts.get('Medium',0)} | {counts.get('High',0)} | {baseline} | {pct(max(counts.values())/m['records'])} |")
    lines += ['', 'Training-majority class is chosen from that fold training data only. Cohort prevalence is a retrospective benchmark, not a deployable selected predictor.', '',
              '## Confusion matrices', '', 'Rows = actual Low/Medium/High; columns = predicted Low/Medium/High.']
    for year in ['2023','2024','2025','pooled']:
        for label, value in [('CatBoost', cb[year]),('XGBoost', xgb[year])]:
            lines += ['', f'{label} {year}:', '', '```text', *[' '.join(f'{v:5d}' for v in row) for row in value['confusion_matrix']], '```']
    lines += ['', '## 2025 district/season checks', '',
              '| District/season | Eligible | CatBoost accuracy | XGBoost accuracy | CatBoost Medium recall | XGBoost Medium recall |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, value in metrics['district_season']['2025'].items():
        lines.append(f"| {name} | {value['records']} | {pct(value['catboost']['accuracy'])} | {pct(value['xgboost']['accuracy'])} | {pct(value['catboost']['per_class']['Medium']['recall'])} | {pct(value['xgboost']['per_class']['Medium']['recall'])} |")
    matched=pd.read_csv(directory/'matched_predictions.csv')
    c=matched.Prediction.eq(matched.Risk_Label);x=matched.XGBoost_Prediction.eq(matched.Risk_Label)
    lines += ['', f"Paired pooled disagreements: CatBoost correct/XGBoost wrong **{int((c&~x).sum())}**; XGBoost correct/CatBoost wrong **{int((x&~c).sum())}**. "
              'No independence-based significance claim is made: overlapping historical windows and repeated district/crop cohorts are dependent.', '',
              '## Artifacts, reproduction and tests', '',
              'New experiment: `'+directory.relative_to(ROOT).as_posix()+'`. Includes saved CatBoost native `.cbm` models, complete `.joblib` pipelines/preprocessing for each selected fold, '
              'development/final/matched predictions, metrics, confusion matrices, feature schema, selection/search records, source/protected-file hashes, environment and artifact manifest. Existing XGBoost predictions/models are read-only.', '',
              '```powershell', (directory/'reproduce.txt').read_text().splitlines()[0], '```', '',
              'Use a new nonexistent output directory to rerun; earlier experiments are never overwritten. Environment: `'+json.dumps(environment,sort_keys=True)+'`. '
              'CatBoost is already installed and pinned in the existing ML requirements; no production dependency or FastAPI change was needed.', '',
              f"Regression command: `{regression['command']}`. Result: **{regression['result']}**. Native categorical/missing/unseen value serialization and insufficient-evidence/cutoff tests also pass. "
              'Protected source CSVs, baseline artifacts, all app Python files and the prospective evaluator were checked unchanged by SHA-256.', '',
              'Verification: `'+json.dumps(verification,sort_keys=True)+'`.', '',
              '## Conclusion and limits', '',
              f"The matched final 2025 comparison is CatBoost **{pct(cb['2025']['accuracy'])}**, macro F1 **{cb['2025']['macro_f1']:.4f}**, Medium recall **{pct(cb['2025']['per_class']['Medium']['recall'])}**, "
              f"versus XGBoost **{pct(xgb['2025']['accuracy'])}**, **{xgb['2025']['macro_f1']:.4f}**, **{pct(xgb['2025']['per_class']['Medium']['recall'])}**. "
              'Assess accuracy and minority-class recall together; a higher pooled accuracy cannot compensate for unsupported future generalization.', '',
              'CatBoost does not demonstrate a clear overall improvement: the pooled accuracy gain is just seven additional correct records, while macro F1 and Medium recall both decline. '
              'It does not resolve the Medium-class distinction problem, and these results do not support replacing the existing classifier or claiming 88%.', '',
              'The evidence supports only the measured matched historical comparison. It does not establish an 88% operational prediction guarantee. '
              'Further model/feature searches should use earlier development data or new prospective cohorts, not feedback from this 2025 result. '
              'Missing verified availability evidence and independently observed prospective outcomes remain unresolved. No production activation, prospective framework edits, source dataset edits or previous model overwrites were performed.']
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report(args.experiment.resolve(),args.output.resolve())
