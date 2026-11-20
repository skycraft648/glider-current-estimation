# 复现与数据边界

## 可以无需私有数据执行的内容

```bash
python scripts/verify_repository.py
pip install -r requirements.txt
python scripts/plot_public_results.py
```

以上只验证仓库统计表一致性并根据**公开汇总结果**画图，**不会重新拟合模型**。

## 需要经过授权才能运行的下游重算

公开脚本 `src/filtered_cohort_analysis.py` 需要两份**不能随仓库公开**的 CSV：

1. `merged_task_estimates.csv`：既有 299 任务 Stage7/Stage8 冻结任务级估计及 CMEMS 参考。沿用原代码字段，例如 `TaskName`, `Date`, `OldResidualU_mps`, `OldResidualV_mps`, `CMEMS500_U_mps`, `CMEMS500_V_mps`, `TimeDepth_U_mps`, `TimeDepth_V_mps`、覆盖率及特征列等。
2. `heading_audit.csv`：仅作为**私人输入**的任务级航向审计汇总，至少具有 `TaskName,TCMRows,NegativeRows,OverflowBandRows,MinHeading,MaxHeading` 列。它来自授权环境内的检查过程，不公开课题组 QC 源码，也不公开逐观测数据。

程序对负值审计与归档样本总数有明确断言。把文件放在本地 `data/private/`（被 `.gitignore` 忽略）：

```bash
pip install -r requirements.txt
python src/filtered_cohort_analysis.py \
  --merged data/private/merged_task_estimates.csv \
  --heading-audit data/private/heading_audit.csv \
  --output outputs/filtered_rerun
```

输出包含任务级中间文件，**不得上传**；`outputs/` 已被 Git 忽略。只有经过授权的统计级结果可以在人工审核后替换 `results/`。

## 实际可重复计算的边界

该脚本会重复执行：筛选 223 任务、计算配对差异、固定日期划分、重新拟合 Ridge/SVR/Random Forest、覆盖率敏感性、日期聚类 Bootstrap，以及任务最大深度的替代参考实验。

不会重复执行：课题组原始 CTD/TCM 质控、原始航向审计生成、上游 MATLAB 动力学模型求解、CMEMS 原始下载/匹配。**“可复现下游计算”不代表“完整独立复现原始实验”。**
