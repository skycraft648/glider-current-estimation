#!/usr/bin/env python3
"""Downstream filtered-cohort analysis using private upstream task-level inputs.
The repository never publishes laboratory quality-control code or raw data.
Private inputs: merged task-level estimates and a per-task heading audit table.
Exclude tasks with negative raw TCM headings in the observed rollover band.
Only the 223 retained tasks enter comparisons and freshly fitted ML models.
Upstream physical estimates and CMEMS samplings are reused, not recomputed.
"""
from pathlib import Path
import argparse
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.multioutput import MultiOutputRegressor
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
parser = argparse.ArgumentParser(description="Filtered-cohort rerun (requires private upstream summary files)")
parser.add_argument("--merged", required=True, type=Path, help="Private merged task-level estimates CSV")
parser.add_argument("--heading-audit", required=True, type=Path, help="Private per-task heading audit CSV")
parser.add_argument("--output", default=Path("outputs/filtered_rerun"), type=Path, help="Output folder, ignored by Git")
args = parser.parse_args()
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
src = args.merged
source=pd.read_csv(src)
assert len(source)==299 and source.TaskName.is_unique
raw=pd.read_csv(args.heading_audit)
merged=source.merge(raw[['TaskName','TCMRows','NegativeRows','OverflowBandRows','MinHeading','MaxHeading']],on='TaskName',how='left',validate='one_to_one')
assert merged.NegativeRows.notna().all(), 'Missing heading audit tasks'
assert (merged.NegativeRows == merged.OverflowBandRows).all(), 'Review negative-heading values outside the observed rollover band before running'
merged['ExcludeHeadingTask']=merged.NegativeRows.gt(0)
merged['RetainedForRecalc']=~merged.ExcludeHeadingTask
merged['ExclusionReason']=np.where(merged.ExcludeHeadingTask,'TCM_NEGATIVE_HEADING_POSSIBLE_INT16_OVERFLOW','')
merged.to_csv(OUT/'01_All299_HeadingExclusionLedger.csv',index=False,encoding='utf-8-sig')
df=merged.loc[~merged.ExcludeHeadingTask].copy()
assert len(df)==223
# Recompute reference error quantities explicitly from original unchanged outputs.
for depth in (500,200):
    avail=df[f'CMEMS{depth}Available'].eq(True)
    df[f'Pair{depth}_Filtered']=df['OldCoverageOK'].eq(True) & df['NewCoverageOK'].eq(True) & avail
    uref=df[f'CMEMS{depth}_U_mps'].to_numpy(float);vref=df[f'CMEMS{depth}_V_mps'].to_numpy(float)
    for label,u,v in [('Old','OldResidualU_mps','OldResidualV_mps'),('GlobalMean','GlobalMeanU_mps','GlobalMeanV_mps'),('LinearCarry','LinearCarryU_mps','LinearCarryV_mps')]:
        df[f'{label}Err{depth}_Recalc_mps']=np.hypot(df[u]-uref,df[v]-vref)

df.to_csv(OUT/'02_Retained223_RecomputedComparisons.csv',index=False,encoding='utf-8-sig')

rows=[]
for depth in (500,200):
 for model in ('Old','GlobalMean','LinearCarry'):
  m=df[f'Pair{depth}_Filtered'] & np.isfinite(df[f'{model}Err{depth}_Recalc_mps'])
  er=df.loc[m,f'{model}Err{depth}_Recalc_mps'].to_numpy(float)
  old=df.loc[m,f'OldErr{depth}_Recalc_mps'].to_numpy(float)
  rows.append({'Reference':f'CMEMS{depth}','Model':model,'PairedN':len(er),'MeanVectorDiff_mps':np.mean(er) if len(er) else np.nan,'MedianVectorDiff_mps':np.median(er) if len(er) else np.nan,'RMSVectorDiff_mps':np.sqrt(np.mean(er**2)) if len(er) else np.nan,'MeanChangeVsOld_mps':np.mean(er-old) if len(er) else np.nan,'ImprovedTasksVsOld':int((er<old).sum())})
physical=pd.DataFrame(rows);physical.to_csv(OUT/'03_Stage7_PhysicalModelMetrics.csv',index=False,encoding='utf-8-sig')

# CMEMS depth reference is a property of time/space/depth, not TCM heading;
# reuse original matched values for retained tasks without re-sampling or relabeling.
refstats=pd.DataFrame([{'Input299':len(merged),'ExcludedTasks':int(merged.ExcludeHeadingTask.sum()),'ExcludedRawHeadingRows':int(merged.loc[merged.ExcludeHeadingTask,'NegativeRows'].sum()),'RetainedTasks':len(df),'RetainedStage7ProcessedOK':int(df.Status.eq('OK').sum()),'RetainedStage7Coverage80':int(df.NewCoverageOK.eq(True).sum()),'RetainedOldCoverage80':int(df.OldCoverageOK.eq(True).sum()),'RetainedCMEMS500Available':int(df.CMEMS500Available.eq(True).sum()),'RetainedCMEMS200Available':int(df.CMEMS200Available.eq(True).sum()),'RetainedPair500':int(df.Pair500_Filtered.sum()),'RetainedPair200':int(df.Pair200_Filtered.sum()),'RetainedTimeDepthOK':int(df.TimeDepthStatus.eq('OK').sum()),'RetainedTimeDepthCoverage80':int((df.TimeDepthCoverageFraction>=0.8).sum()),'RetainedTimeDepth100':int(np.isclose(df.TimeDepthCoverageFraction,1).sum())}]);refstats.to_csv(OUT/'00_RecalculationAudit.csv',index=False,encoding='utf-8-sig')

mask=(df.Pair500_Filtered)&df.TimeDepthCoverageFraction.ge(.8)&df.TimeDepthStatus.eq('OK')&np.isfinite(df.TimeDepth_U_mps)&np.isfinite(df.TimeDepth_V_mps)
ml=df.loc[mask].copy();ml['Date']=pd.to_datetime(ml.Date)
def split(x):
 if x<=pd.Timestamp('2025-09-10'):return 'train'
 if x<=pd.Timestamp('2025-09-22'):return 'validation'
 return 'test'
ml['MLSplit']=ml.Date.map(split)
assert ml.MLSplit.nunique()==3
ml['DaySin']=np.sin(2*np.pi*ml.Date.dt.dayofyear/365.25)
ml['DayCos']=np.cos(2*np.pi*ml.Date.dt.dayofyear/365.25)
ml['GroundEast_mps']=ml.GPS_East_m/ml.Duration_s
ml['GroundNorth_mps']=ml.GPS_North_m/ml.Duration_s
ml['MissingFraction']=1-ml.CoverageFraction
features=['MidLon','MidLat','DaySin','DayCos','Duration_s','MaxDepth_m','CoverageFraction','MissingFraction','GroundEast_mps','GroundNorth_mps','OldResidualU_mps','OldResidualV_mps','GlobalMeanU_mps','GlobalMeanV_mps','LinearCarryU_mps','LinearCarryV_mps']
X=ml[features];base=ml[['OldResidualU_mps','OldResidualV_mps']].to_numpy(float);y=ml[['TimeDepth_U_mps','TimeDepth_V_mps']].to_numpy(float)
assert np.isfinite(X.to_numpy(float)).all()
tr=ml.MLSplit.eq('train').to_numpy();va=ml.MLSplit.eq('validation').to_numpy();te=ml.MLSplit.eq('test').to_numpy()
models={'Ridge':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=10.0)),
 'SVR':make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),MultiOutputRegressor(SVR(kernel='rbf',C=0.1,epsilon=0.025))),
 'RandomForest':make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(n_estimators=300,min_samples_leaf=8,max_features=0.8,random_state=20261017,n_jobs=1))}
refmean=y[tr].mean(axis=0)
predictions={'OldModel':base,'GlobalMean':ml[['GlobalMeanU_mps','GlobalMeanV_mps']].to_numpy(float),'LinearCarry':ml[['LinearCarryU_mps','LinearCarryV_mps']].to_numpy(float),'ZeroCurrent':np.zeros_like(y),'TrainMeanCMEMS':np.repeat(refmean.reshape(1,2),len(y),axis=0)}
for name,est in models.items():
 est.fit(X.loc[tr],y[tr]-base[tr]);predictions[name]=base+est.predict(X)
def stats(pred,actual):
 v=pred-actual;norm=np.linalg.norm(v,axis=1)
 return {'N':len(norm),'MeanVectorDiff_mps':float(norm.mean()),'MedianVectorDiff_mps':float(np.median(norm)),'RMSVectorDiff_mps':float(np.sqrt(np.mean(norm**2))),'MeanU_Bias_mps':float(v[:,0].mean()),'MeanV_Bias_mps':float(v[:,1].mean())}
chosen=min(models, key=lambda name:stats(predictions[name][va],y[va])['MeanVectorDiff_mps'])
metrics=[]
for s,m in [('train',tr),('validation',va),('test',te)]:
 for label,pred in predictions.items():metrics.append({'Split':s,'Model':label,'SelectedOnValidation':label==chosen,**stats(pred[m],y[m])})
met=pd.DataFrame(metrics);met.to_csv(OUT/'04_Stage8_RetrainedML_Metrics.csv',index=False,encoding='utf-8-sig')
pred=ml[['TaskName','Date','MLSplit','TimeDepth_U_mps','TimeDepth_V_mps','TimeDepthCoverageFraction']].copy()
for name,yhat in predictions.items():
 pred[f'{name}_U_mps']=yhat[:,0];pred[f'{name}_V_mps']=yhat[:,1];pred[f'{name}_VectorDiff_mps']=np.linalg.norm(yhat-y,axis=1)
pred.to_csv(OUT/'05_Stage8_RetrainedML_Predictions.csv',index=False,encoding='utf-8-sig')
ml[['TaskName','Date','MLSplit','NegativeRows','Pair500_Filtered','TimeDepthCoverageFraction']].to_csv(OUT/'06_StudyCohort_SplitLedger.csv',index=False,encoding='utf-8-sig')

# Same paired cohort for sensitivity and calendar-date bootstrap.
sens=[]
for thr in (.80,.85,.90,.95):
 selection=(df.OldCoverageFraction.ge(thr)&df.CoverageFraction.ge(thr)&df.CMEMS500Available.eq(True)&df.Status.eq('OK'))
 for mdl in ('Old','GlobalMean','LinearCarry'):
  e=df.loc[selection,f'{mdl}Err500_Recalc_mps'].to_numpy(float)
  sens.append({'CoverageThreshold':thr,'Model':mdl,'N':len(e),'MeanVectorDiff_mps':e.mean() if len(e) else np.nan})
pd.DataFrame(sens).to_csv(OUT/'07_CoverageThresholdSensitivity.csv',index=False,encoding='utf-8-sig')
months=[]
for period,group in df[df.Pair500_Filtered].groupby(pd.to_datetime(df[df.Pair500_Filtered].Date).dt.strftime('%Y-%m')):
 months.append({'Month':period,'N':len(group),'OldMean':group.OldErr500_Recalc_mps.mean(),'GlobalMean':group.GlobalMeanErr500_Recalc_mps.mean(),'LinearCarryMean':group.LinearCarryErr500_Recalc_mps.mean()})
pd.DataFrame(months).to_csv(OUT/'08_MonthlyResults.csv',index=False,encoding='utf-8-sig')

# Cluster bootstrap by date, deterministic seed, 3000 resamples, percentile 2.5/97.5.
rng=np.random.default_rng(20261118)
boot=[]
for depth in (500,200):
 d=df[df[f'Pair{depth}_Filtered']].copy();d['Date']=pd.to_datetime(d.Date)
 gr=[g for _,g in d.groupby('Date')];n=len(gr)
 ds=[]
 for i in range(3000):
  ix=rng.integers(0,n,size=n)
  v=np.concatenate([ (gr[j][f'LinearCarryErr{depth}_Recalc_mps']-gr[j][f'OldErr{depth}_Recalc_mps']).to_numpy() for j in ix]);ds.append(v.mean())
 vals=(d[f'LinearCarryErr{depth}_Recalc_mps']-d[f'OldErr{depth}_Recalc_mps']).to_numpy()
 boot.append({'Reference':f'CMEMS{depth}','N':len(d),'Dates':n,'MeanChangeLinearMinusOld_mps':np.mean(vals),'BootstrapP2_5_mps':np.quantile(ds,0.025),'BootstrapP97_5_mps':np.quantile(ds,0.975),'Bootstraps':3000})
pd.DataFrame(boot).to_csv(OUT/'09_DayClusterBootstrap.csv',index=False,encoding='utf-8-sig')

# Spatial grid using 0.1 deg same coarse scope; no attempt to reconstruct underwater location.
sp=df[df.Pair500_Filtered].copy()
sp['GridLon']=np.floor(sp.MidLon*10)/10;sp['GridLat']=np.floor(sp.MidLat*10)/10
sp['DeltaLMinusOld500']=sp.LinearCarryErr500_Recalc_mps-sp.OldErr500_Recalc_mps
sg=sp.groupby(['GridLon','GridLat']).agg(N=('TaskName','size'),Dates=('Date','nunique'),MeanChange=('DeltaLMinusOld500','mean')).reset_index().sort_values('N',ascending=False)
sg.to_csv(OUT/'10_SpatialGrid.csv',index=False,encoding='utf-8-sig')

# Summary text for the downstream filtered-cohort deliverable
with open(OUT/'README_复算规则与限制.txt','w',encoding='utf-8') as f:
 f.write('筛除疑似异常航向任务后的下游分析与重新训练\n')
 f.write('本次剔除规则：原始TCM任何航向h<0且位于[-327.68,-295]范围，则整任务剔除。\n')
 f.write('注意负值可能是int16数值编码问题，并非坏传感器读数；这是保守剔除敏感性分析，非最终解码的物理真值。\n')
 f.write('只读既有CTD/TCM/CMEMS；对保留任务使用此前冻结的Old/GlobalMean/LinearCarry逐任务估计，不对原质控重新运行、不对未剔除任务重复做MATLAB。\n')
 f.write('整个评价链已对保留任务重新筛选配对任务、重新计算矢量误差、重新拟合Ridge/SVR/RandomForest并重新评估基准。\n')
 f.write('实验中CMEMS仍是模式参考；绝不是现场真实DAC。原报告的299任务、260配对等数字不得照抄到新结果。\n')
 f.write('同日任务非独立，日聚类3000次Bootstrap仅为稳健性分析。\n')
 f.write('未剔除的记录正向最大航向327.67度，并非360全圆覆盖；这意味着严格剔除策略可能引入选择偏差。\n')
 f.write('机器学习训练/验证/测试按原日期阈值不变；未对测试集进行超参调节。\n')
 f.write('数值结果详见00-10编号CSV。\n')

# 3 report-facing figures
plt.rcParams.update({'font.size':10})
fig,ax=plt.subplots(figsize=(7.5,4.2));selected=physical[physical.Reference.eq('CMEMS500')];bars=ax.bar(selected.Model,selected.MeanVectorDiff_mps);ax.set_title('Stage7 original models | negative-heading tasks excluded');ax.set_ylabel('Mean vector difference vs CMEMS 0-500 m (m/s)');ax.grid(axis='y',alpha=.25)
for b,val in zip(bars,selected.MeanVectorDiff_mps):ax.text(b.get_x()+b.get_width()/2,val+0.001,f'{val:.5f}',ha='center',fontsize=9)
fig.tight_layout();fig.savefig(OUT/'Figure1_Stage7_AfterExclusion.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.8));test=met[met.Split.eq('test')].sort_values('MeanVectorDiff_mps',ascending=True); ax.barh(test.Model,test.MeanVectorDiff_mps);ax.set_xlabel('Mean vector difference vs time-depth CMEMS (m/s)');ax.set_title('Independent date test | models retrained after task exclusion');ax.grid(axis='x',alpha=.25)
fig.tight_layout();fig.savefig(OUT/'Figure2_ML_AfterExclusion.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.5,4.2));sensdf=pd.DataFrame(sens);
for name in ('Old','GlobalMean','LinearCarry'):
 x=sensdf[sensdf.Model.eq(name)];ax.plot(x.CoverageThreshold*100,x.MeanVectorDiff_mps,marker='o',label=name)
ax.legend();ax.set_xlabel('Coverage threshold (%)');ax.set_ylabel('Mean vector difference (m/s)');ax.set_title('Threshold sensitivity after heading-based exclusion');ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(OUT/'Figure3_Sensitivity_AfterExclusion.png',dpi=170);plt.close(fig)

print('\nAUDIT\n',refstats.to_string(index=False))
print('\nSTAGE7\n',physical.to_string(index=False))
print('\nML SPLIT\n',ml.MLSplit.value_counts().to_string())
print('\nMODEL METRICS TEST\n',met[met.Split.eq('test')].to_string(index=False))
print('\nCHOSEN',chosen)
print('\nBOOTSTRAP\n',pd.DataFrame(boot).to_string(index=False))
print('\nMONTHLY\n',pd.DataFrame(months).to_string(index=False))
print('\nSPATIAL TOP\n',sg.head(3).to_string(index=False))
# Additional identical ML evaluation with task-specific maximum-depth CMEMS reference
# for report 4.5 sensitivity. The cohort and date partitions match the main ML.
try:
    taskdepth=ml[['CMEMS_TaskDepth_U_mps','CMEMS_TaskDepth_V_mps']].to_numpy(float)
    if np.isfinite(taskdepth).all():
        preds={'ZeroCurrent':np.zeros_like(taskdepth),'OldModel':base,'GlobalMean':predictions['GlobalMean'],'LinearCarry':predictions['LinearCarry']}
        for name,est in models.items():
            alt=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=10.0)) if name=='Ridge' else (make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),MultiOutputRegressor(SVR(kernel='rbf',C=0.1,epsilon=0.025))) if name=='SVR' else make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(n_estimators=300,min_samples_leaf=8,max_features=.8,random_state=20261017,n_jobs=1)))
            alt.fit(X.loc[tr],taskdepth[tr]-base[tr]);preds[name]=base+alt.predict(X)
        altrows=[]
        for splitname,msk in [('train',tr),('validation',va),('test',te)]:
            for name,p in preds.items():altrows.append({'Split':splitname,'Model':name,**stats(p[msk],taskdepth[msk])})
        altmet=pd.DataFrame(altrows);altmet.to_csv(OUT/'11_TaskDepthReference_RetrainedML_Metrics.csv',index=False,encoding='utf-8-sig')
        print('TASK-DEPTH SENSITIVITY TEST\n',altmet[altmet.Split.eq('test')][['Model','MeanVectorDiff_mps','N']].to_string(index=False))
except Exception as e:
    print('Task-depth sensitivity unavailable:',e)
