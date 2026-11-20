# Underwater Glider Current Estimation: Filtered-Cohort Analysis

**Scope:** This repository contains **only the final conservative task-exclusion analysis (Nov 18, 2026)**. Laboratory-provided quality-control source code, raw CTD/TCM files, CMEMS inputs, task-level records, and private MATLAB implementations are not published.

This research compares frozen glider task-level physical estimates with CMEMS *numerical-model* references after excluding tasks with potentially rolled-over negative heading values. The analysis recalculates paired statistics, retrains Ridge/SVR/Random Forest with chronological train/validation/test splits, and evaluates zero-current baselines and sensitivity checks.

**Cohort:** 299 initial tasks; 76 excluded; **223 retained**, with **193** valid 0–500 m paired comparisons. ML splits: **113 train / 16 validation / 64 test**.

**Test mean vector difference against time–depth CMEMS (m/s):** zero-current baseline **0.04652**, Ridge **0.06588**, Random Forest **0.07288**, SVR **0.11214**. The learned models do **not** outperform the zero-current baseline on the held-out dates. CMEMS is not an independent observation of actual currents.

The public code starts **after** group-provided upstream preprocessing and reuses frozen upstream estimates; it does not implement or reproduce the lab QC pipeline. Public summary tables and plots can be checked via `python scripts/verify_repository.py`. Full downstream reruns require authorized private input tables; see [reproducibility](docs/REPRODUCIBILITY.md).

Before making this repository public, obtain appropriate approval for publishing derived aggregate results and figures.
