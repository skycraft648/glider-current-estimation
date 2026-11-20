"""Validate only public aggregated results and publication boundaries (stdlib)."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'results' / 'tables'

def rows(name):
    with (TABLE / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

cohort = rows('cohort_summary.csv')[0]
assert int(cohort['Input299']) == 299
assert int(cohort['ExcludedTasks']) == 76
assert int(cohort['RetainedTasks']) == 223
assert int(cohort['RetainedPair500']) == 193
assert int(cohort['RetainedPair200']) == 199
ml = rows('ml_split_metrics.csv')
for split, count in [('train', 113), ('validation', 16), ('test', 64)]:
    assert all(int(x['N']) == count for x in ml if x['Split'] == split)
    assert any(x['Split'] == split for x in ml)
test = {x['Model']:float(x['MeanVectorDiff_mps']) for x in ml if x['Split'] == 'test'}
assert test['ZeroCurrent'] < test['Ridge'] < test['RandomForest'] < test['SVR'] < test['OldModel']
assert not (ROOT / 'src' / 'matlab').exists(), 'MATLAB lab-source directory must not be distributed'
assert not (ROOT / 'src' / 'qc').exists(), 'QC source should never be published'
assert not (ROOT / 'data').exists(), 'Private data present in release directory'
assert not (ROOT / 'outputs').exists(), 'Task-level outputs present in release directory'
assert len(list(ROOT.rglob('*.m'))) == 0, 'MATLAB source in public release'
print('PASS: filtered cohort, test metrics and publication boundary checks')
