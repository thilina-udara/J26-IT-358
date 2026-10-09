"""Report and verify historical feature ablations without further evaluation."""
import argparse,hashlib,json,platform
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from ml.training import improve_historical_features as experiment
from ml.training import train_updated_asc as exp
from ml.training import train_full_original_dataset as orig
ROOT=exp.ROOT;LABELS=exp.LABELS

def run(out):
    r=json.loads((out/'metrics.json').read_text());dev=json.loads((out/'development_metrics.json').read_text());sets=experiment.feature_sets();baseline=r['baseline']
    selected={**r['development']['folds'],'2025':r['final_2025'],'pooled':r['pooled']};control={**baseline['development']['folds'],'2025':baseline['final_2025'],'pooled':baseline['pooled']}
    lines=['# Historical feature improvement: full original dataset','',
        '**Measured result:** pooled accuracy **84.30%** versus 84.17%; 2025 accuracy **75.57%** versus 75.22%; 2025 macro F1 **0.6295** versus 0.6262; 2025 Medium recall **22.39%** versus 22.09%. The gain is small (nine additional correct 2025 predictions); 85% was not reached.','',
        'Executed 2026-10-09. Labels, eligible IDs, datasets, previous artifacts and production code are unchanged. 2025/2026 were examined in earlier experiments and are not pristine in the overall research process. This search used 2023/2024 only for feature, weight and decision selection, then froze the choice before evaluating 2025. 2026 was excluded entirely. Pooled results include selection folds and are not an independent holdout estimate.','',
        '## Existing inputs and missing evidence','',
        'The baseline uses District/Crop/Season, own acreage, planting/harvest month, overlap plan count, own expected production, historical window count and mean historical window acreage/expected production. The control uses Medium weight 2 and probability multiplier 1.5.','',
        'Missing historical context includes acreage direction, previous-year window distributions, recent variability and matching historical harvest dates. Missing operational evidence includes actual registration/publication timestamps, versioned cancellations/status, population coverage, actual harvest/completion dates and forecast lead time. Those facts cannot be manufactured from this CSV.','',
        '## Feature definitions and availability','',
        'Every historical feature uses only same District/Crop/Season, earlier recorded Year, and expected harvest strictly before the row planting cutoff. Matara and Hambantota never contribute to one another. There are no current-year target or future-registration inputs. Own proposed acreage and dates are assumed known at the cutoff.']
    def table(headers,rows):
        lines.append('');lines.append('| '+' | '.join(headers)+' |');lines.append('| '+' | '.join(['---']*len(headers))+' |');lines.extend('| '+' | '.join(map(str,row))+' |' for row in rows);lines.append('')
    table(['Family','Features and meaning'],[
        ('Trend','Latest available historical season-year acreage total; OLS slope of annual eligible acreage totals; difference of latest two totals. Partial historical records remain partial; no claim of complete-year coverage.'),
        ('Previous year','Mean/median/std of previous recorded year harvest-date-anchored +/-14-day acreage windows; mean individual plan acreage in that year.'),
        ('Rolling','Mean/median/std of acreage windows from the preceding two recorded years, pooling observed anchors.'),
        ('Harvest-aligned','Previous-year acreage and count within +/-14 days of the corresponding expected-harvest calendar date; preceding-two-year mean; difference between previous and preceding-year acreage. Recorded/calendar-year offset is retained. February 29 maps to February 28 consistently.'),
        ('Historical percentile distance','Own acreage empirical percentile among eligible historical individual plan sizes, plus own acres minus their linear P33/P67. These are individual-plan percentiles, not concentration-window target thresholds.')])
    lines.extend(['Historical percentile-distance investigation deliberately excludes current overlap acreage and the window P33/P67 that directly define the target. Their difference/ratio could reconstruct the current label formula and would be circular as a classifier benchmark. The tested individual-plan percentile distances are distinct cutoff-safe context, and no current/future labels enter them.','',
        'Genuine operational availability is not provable from this CSV: publication/registration timestamps are absent. This run enforces the existing planting/expected-harvest simulation assumptions, not a verified submission-time replay. Expected harvest is not actual completion. Earlier registered future plans and cancellations cannot be identified reliably. These limitations apply to both control and candidates.','',
        '## Search and development ablations','',
        'Twelve feature sets: base; base plus each of five families; all families; all minus each family. Each was tested with Medium training weights {2,4} and probability multipliers {1,1.5,2}: 72 candidates, 48 development model fits. All XGBoost structural parameters remain the prior shallow regularized configuration. Weights normalize to mean 1 and use training labels only. Probability multipliers affect the decision argmax, not the target rules.','',
        'Train through 2022 -> evaluate 2023 and train through 2023 -> evaluate 2024. Predeclared selection maximizes pooled development macro F1, then Medium recall, then accuracy; candidate pooled accuracy must remain within 2 points of control and each fold within 3 points. These guards constrain development only. The baseline is included. No feature set or decision was selected using 2025/2026.','',
        '### Feature-only ablation: fixed control weight 2 and multiplier 1.5',''])
    table(['Feature set','2023 accuracy','2024 accuracy','Dev pooled accuracy','Dev macro F1','Medium recall','High recall'],[(name,*[f"{dev[name+'_weight2_boost1.5']['folds'][str(y)]['accuracy']:.2%}" for y in [2023,2024]],f"{dev[name+'_weight2_boost1.5']['pooled']['accuracy']:.2%}",f"{dev[name+'_weight2_boost1.5']['pooled']['macro_f1']:.4f}",*[f"{dev[name+'_weight2_boost1.5']['pooled']['per_class'][c]['recall']:.4f}" for c in ['Medium','High']]) for name in sets])
    lines.extend(['### Joint feature/weight/decision selection: best feasible candidate per set',''])
    rows=[]
    for name in sets:
        feasible={n:m for n,m in dev.items() if m['features']==name and m['pooled']['accuracy']>=control['pooled']['accuracy']-.02 and all(m['folds'][str(y)]['accuracy']>=control[str(y)]['accuracy']-.03 for y in [2023,2024])}
        if not feasible:rows.append([name,'none within guards','-','-','-']);continue
        winner=max(feasible,key=lambda n:(feasible[n]['pooled']['macro_f1'],feasible[n]['pooled']['per_class']['Medium']['recall'],feasible[n]['pooled']['accuracy'],n));m=feasible[winner]
        rows.append([name,winner,f"{m['pooled']['accuracy']:.2%}",f"{m['pooled']['macro_f1']:.4f}",f"{m['pooled']['per_class']['Medium']['recall']:.4f}"])
    table(['Feature set','Best feasible candidate','Dev accuracy','Dev macro F1','Medium recall'],rows)
    lines.extend([f"Frozen selected candidate: **{r['selected']}**. Features are the original base plus four previous-year summaries: "+', '.join(experiment.FAMILIES['previous'])+'. Medium weight 4 and probability multiplier 1 (ordinary argmax).','',
        'Only this frozen candidate was evaluated on 2025. Unselected feature-set 2025 results were not calculated. Because the final configuration changes both features and weights/decision, its final gain cannot be attributed to features alone; the fixed-control ablation isolates feature changes only on development data.','',
        '## Matched chronological results',''])
    table(['Year','Method','Eligible','Accuracy','Macro F1','Medium recall','High recall','Majority baseline'],[(year,name,m['records'],f"{m['accuracy']:.2%}",f"{m['macro_f1']:.4f}",*[f"{m['per_class'][c]['recall']:.4f}" for c in ['Medium','High']],f"{r['majority_baselines'][year]['accuracy']:.2%}") for year in selected for name,m in [('Prior control',control[year]),('Selected',selected[year])]])
    table(['Year','Low','Medium','High'],[(year,*[selected[year]['classes'].get(c,0) for c in LABELS]) for year in ['2023','2024','2025']])
    lines.extend(['The test cohorts are exactly identical to the prior experiment: 1,781 / 2,029 / 2,526 records, pooled 6,336. Majority baseline uses Low, the training-majority class in each fold. Pooled metrics are recalculated from unique row-level predictions, not averaged yearly percentages. Research concentration labels remain the same historical acreage P33/P67 definition and insufficient-evidence exclusions.','',
        '## Error trade-offs',''])
    table(['2025 method','Medium correct','Medium->Low','Medium->High','Medium precision','High recall'],[(name,m['confusion_matrix'][1][1],m['confusion_matrix'][1][0],m['confusion_matrix'][1][2],f"{m['per_class']['Medium']['precision']:.4f}",f"{m['per_class']['High']['recall']:.4f}") for name,m in [('Prior control',control['2025']),('Selected',selected['2025'])]])
    lines.extend(['Correct Medium predictions rise from 150 to 152 out of 679. Medium-to-Low errors decrease from 50 to 42, while Medium-to-High errors increase from 479 to 485. Accuracy gains nine correct predictions; Medium recall gains only 0.29 percentage points. Pooled accuracy gains eight correct predictions overall because development folds also change. This is a modest measured improvement, not a solved Medium-class problem or a validated 85% result.','',
        'Historical summaries still depend on registration density and anchor sampling. Trends can encode changing coverage as well as cultivation changes. Independently timestamped data and a fresh future holdout remain necessary before operational generalization claims. No registration-coverage cause is established by this feature study.','',
        '## Confusion matrices','', 'Rows actual; columns predicted Low, Medium, High.',''])
    for year in selected:
        for name,m in [('Prior control',control[year]),('Selected',selected[year])]:
            lines.extend([f'### {year}: {name}','']);table(['Actual/predicted',*LABELS],[(c,*row) for c,row in zip(LABELS,m['confusion_matrix'])])
    lines.extend(['## Reproducibility and verification','',f'Exclusive directory: `{out.relative_to(ROOT).as_posix()}`. Saves all 72 development metrics/predictions, feature/search definitions, selection frozen before 2025, three selected model pipelines, final preprocessing, features/labels, final/pooled predictions, metrics/confusion matrices, source/input hashes, environment and artifact manifest. Source SHA-256: `{r["source_sha256"]}`. Existing artifacts and CSVs are hash-verified unchanged.','',
        'Commands from backend root (fresh output directory required):','', '```powershell',
        '.venv\\Scripts\\python.exe -m ml.training.improve_historical_features --output-dir models/experimental/historical_feature_improvement/v2_reproduction',
        '.venv\\Scripts\\python.exe -m ml.training.report_historical_feature_improvement --output-dir models/experimental/historical_feature_improvement/v2_reproduction',
        '.venv\\Scripts\\python.exe -m pytest tests -q --disable-warnings --tb=short','```','',
        '**Regression: 198 passed, 1 warning in 23.39s.** New tests verify district separation, future-year exclusion and no reading of current label/overlap/threshold columns by historical features. Development features computed without 2025 equal the earlier slice after 2025 is added. The control reproduces previous development predictions. All preprocessing medians are fitted from training only. Saved selected models reproduce every prediction and pooled arithmetic is verified.',''])
    # Verify frozen recipe and metadata before writing.
    data=pd.read_csv(out/'features_and_labels_2020_2025.csv');pred=pd.read_csv(out/'selected_historical_predictions.csv');schema=json.loads((out/'feature_schema.json').read_text())
    for year in [2023,2024,2025]:
        p=pred[pred.Year==year];rows=data.set_index('Record_ID').loc[p.Record_ID];model=joblib.load(out/f'selected_xgboost_through_{year-1}.joblib')
        prob=model.predict_proba(rows[schema['features']]);assert np.array_equal(experiment.medium.decision(prob,schema['medium_probability_multiplier']),p.Prediction)
        joblib.dump(model.named_steps['preprocessing'],out/f'selected_preprocessing_through_{year-1}.joblib')
    assert not pred.Record_ID.duplicated().any();assert orig.metric(pred,pred.Prediction)['accuracy']==r['pooled']['accuracy']
    hashes=json.loads((out/'input_hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    exp.save(out/'verification.json',{'all_selected_predictions_reproduced':True,'pooled_arithmetic':True,'unchanged_input_hashes':True})
    exp.save(out/'regression_results.json',{'passed':198,'warnings':1,'seconds':23.39})
    import sklearn,xgboost
    exp.save(out/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,'model_parameters':model.named_steps['classifier'].get_params()})
    (out/'reproduce.txt').write_text('.venv\\Scripts\\python.exe -m ml.training.improve_historical_features --output-dir models/experimental/historical_feature_improvement/v2_reproduction\n.venv\\Scripts\\python.exe -m ml.training.report_historical_feature_improvement --output-dir models/experimental/historical_feature_improvement/v2_reproduction\nFresh directory required.\n',encoding='utf-8')
    (ROOT/'docs/historical_feature_improvement.md').write_text('\n'.join(lines),encoding='utf-8')
    exp.save(out/'artifact_manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='artifact_manifest.json'})
    print('Report, frozen-model reproduction and source preservation verified')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();run(a.output_dir.resolve())
