"""Draw a public chart from aggregate filtered ML metrics only."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
p = root / 'results' / 'tables' / 'ml_split_metrics.csv'
with p.open(encoding='utf-8-sig', newline='') as f:
    tests = [x for x in csv.DictReader(f) if x['Split'] == 'test']
tests.sort(key=lambda x: float(x['MeanVectorDiff_mps']))
fig, ax = plt.subplots(figsize=(9,4.8))
ax.barh([t['Model'] for t in tests], [float(t['MeanVectorDiff_mps']) for t in tests])
ax.set_xlabel('Mean vector difference vs CMEMS model reference (m/s)')
ax.set_title('Filtered cohort: held-out date test (N=64)')
ax.invert_yaxis()
ax.grid(axis='x',alpha=0.25)
fig.tight_layout()
target = root / 'results' / 'figures' / 'public_ml_test_from_summary.png'
fig.savefig(target,dpi=160)
print(f'Created {target}')
