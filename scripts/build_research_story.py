"""Add an answer-first research report; never refit or overwrite earlier analyses."""
from pathlib import Path
from datetime import datetime, timezone
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hashlib
import json
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".codex/python-packages"))
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/research_story'
OUT.mkdir(exist_ok=True)
STAMP = datetime.now(timezone.utc).isoformat()
INPUTS = {}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name, **kw):
    p = ROOT / name
    INPUTS[name] = sha(p)
    return pd.read_csv(p, **kw)

handoff = Path(r'D:\ALL THINGS\Downloads\Property_Tax_Assessment_Project_Agent_Handoff.docx')
with ZipFile(handoff) as z:
    xml = ET.fromstring(z.read('word/document.xml'))
    paragraphs = [''.join(n.itertext()) for n in xml.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')]
(OUT/'initial_brief.txt').write_text('\n'.join(paragraphs), encoding='utf-8')

sales = read('data/processed/sales_clean.csv', dtype={'parcel_id': str})
s = sales.loc[sales.sale_year.eq(2017)].copy()
assert len(s) == 8595 and s.parcel_id.notna().all()
unique = s.sort_values(['sale_date','record_id']).drop_duplicates('parcel_id', keep='last')
pred = {c: read(f'outputs/conditional/{c}_predictions.csv') for c in ['main','positive_garage']}

def proportionality(frame, label, cluster, p='sale_price', a='assessed_value'):
    x = np.log(frame[p].to_numpy(float)); y = np.log(frame[a].to_numpy(float))
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]; residual = y-X@b
    codes, labels = pd.factorize(frame[cluster]); G = len(labels); n = len(x)
    sums = np.zeros((G, 2)); np.add.at(sums, codes, X*residual[:,None])
    bread = np.linalg.inv(X.T@X)
    covariance = (G/(G-1))*((n-1)/(n-2))*bread@(sums.T@sums)@bread
    se = np.sqrt(covariance[1,1]); t = (b[1]-1)/se
    ci = stats.t.ppf(.975,G-1)*se
    Q, R = np.linalg.qr(X, mode='reduced')
    influence = np.linalg.solve(R, (Q*residual[:,None]).T).T
    cluster_influence = np.zeros((G,2)); np.add.at(cluster_influence,codes,influence)
    reference = cluster_influence.T@cluster_influence * G/(G-1)*(n-1)/(n-2)
    assert np.allclose(reference, covariance, rtol=1e-7, atol=1e-12)
    r = np.corrcoef(x,y)[0,1]; r2 = 1-residual@residual/np.sum((y-y.mean())**2)
    assert np.isclose(r*r,r2,atol=1e-12)
    return dict(sample=label,n=n,clusters=G,cluster=cluster,pearson=np.corrcoef(frame[p],frame[a])[0,1],
                log_pearson=r,ols_r2=r2,beta=b[1],se=se,t=t,df=G-1,
                p_value=2*stats.t.sf(abs(t),G-1),ci_low=b[1]-ci,ci_high=b[1]+ci,
                intercept=b[0],q_mean=float(np.mean(frame[p]/frame[a])))

slopes = pd.DataFrame([
    proportionality(s,'全部2017交易 / All 2017 sales','parcel_id'),
    proportionality(unique,'每房屋最新一笔 / Latest per parcel','parcel_id'),
    proportionality(pred['main'],'主组合样本 / Main cohort','grid2km','sale_price_usd','assessed_value_usd')])
slopes.to_csv(OUT/'proportionality.csv',index=False)

scores=[]
for c,p in pred.items():
    for scheme in ['spatial','forward']:
        for model in ['original','global','additive','interaction']:
            m=p[f'{scheme}_{model}'].notna(); q=p.loc[m,'ratio'].to_numpy(); qhat=p.loc[m,f'{scheme}_{model}'].to_numpy()
            direct = 1-np.sum((q-qhat)**2)/np.sum((q-q.mean())**2)
            scores.append(dict(cohort=c,scheme=scheme,model=model,n=len(q),r2=direct,
                direct_q_rmse=np.sqrt(np.mean((q-qhat)**2)),calibrated_ratio_rmse=np.sqrt(np.mean((q/qhat-1)**2))))
scores=pd.DataFrame(scores);scores.to_csv(OUT/'prediction_scores.csv',index=False)
perf=read('outputs/conditional/performance.csv')
check=scores.merge(perf,on=['cohort','scheme','model','n'],validate='one_to_one')
assert np.allclose(check.calibrated_ratio_rmse,check.ratio_rmse,atol=1e-12)
bands=read('outputs/exploration/price_bands_2017.csv')
gains=read('outputs/conditional/performance_gains.csv')
thresholds=read('outputs/group_bias/threshold_counts.csv')
cells=read('outputs/conditional/四格组均值_Four_Cell_Means.csv')
orders=read('outputs/group_algebra/main_orders.csv')
scope=read('outputs/conditional/source_scope.csv')

blocks=[];charts=[];tables=[];datasets={};sources=[];markdown=[]
db=sqlite3.connect(OUT/'report_source.sqlite')

def prose(id,body,source=None):
    block=dict(id=id,type='markdown',body=body,layout='full')
    if source:block['sourceId']=source
    blocks.append(block);markdown.append(body)

def dataset(id,frame,inputs,definition):
    datasets[id]=json.loads(frame.to_json(orient='records',force_ascii=False))
    frame.to_sql(id,db,if_exists='replace',index=False)
    assert len(pd.read_sql_query(f'SELECT * FROM "{id}"',db))==len(frame)
    sources.append(dict(id=id,label=definition,path=f'outputs/research_story/{id}.csv',
        inputFiles=inputs,transformation='scripts/build_research_story.py; saved-result selection or explicitly documented new Python calculation.',
        query=dict(engine='SQLite / outputs/research_story/report_source.sqlite',language='sql',sql=f'SELECT * FROM "{id}";',
          tables_used=[id],description='Display query over verified Python results, not a statistical fit. '+definition)))
    frame.to_csv(OUT/f'{id}.csv',index=False)

def chart(id,title,type,x,y,source,color=None,reference=None):
    enc={'x':{'field':x,'type':'ordinal'},'y':{'field':y,'type':'quantitative'}}
    if color:enc['color']={'field':color,'type':'nominal'}
    spec=dict(id=id,title=title,type=type,dataset=source,sourceId=source,layout='full',encodings=enc,
              xAxisTitle=x,yAxisTitle=y,valueFormat='number',settings={'sort':'none','showPoints':'always'},maxRows=100)
    if reference is not None:spec['referenceLines']=[dict(value=reference,axis='y',label=str(reference),lineStyle='dashed',color='neutral')]
    charts.append(spec);blocks.append(dict(id=id+'-block',type='chart',chartId=id,layout='full'))

def table(id,title,source,columns):
    tables.append(dict(id=id,title=title,dataset=source,sourceId=source,layout='full',density='spacious',
        defaultSort={'field':columns[0][0],'direction':'asc'},columns=[dict(field=a,label=b,format=c) for a,b,c in columns]))
    blocks.append(dict(id=id+'-block',type='table',tableId=id,layout='full'))

dataset('proportionality',slopes,['data/processed/sales_clean.csv','outputs/conditional/main_predictions.csv'],
        'Log-assessment OLS; CR1 cluster covariance; two-sided t(G−1) reference for H0: beta=1. Conditional on retained data, not population sampling.')
dataset('prediction_scores',scores,['outputs/conditional/main_predictions.csv','outputs/conditional/positive_garage_predictions.csv'],
        'Direct held-out q R² against evaluation-sample mean, distinct from calibrated ratio RMSE; fixed existing predictions, no refitting.')
dataset('price_bands',pd.DataFrame({'价格档 / Price band':bands.price_band_label,'中位比率 % / Median q':bands.median_ratio*100,'n':bands.n}),
        ['outputs/exploration/price_bands_2017.csv'],'Median P/A by unequal-width price categories, all 8595 clean 2017 sales; not group arithmetic means.')
tails=thresholds.loc[thresholds.cohort.eq('main') & thresholds.basis.eq('global_scaled')].groupby('min_n',as_index=False).agg(groups=('biased_groups','sum'),eligible=('eligible_groups','max'))
tails['最少交易数 / Minimum n']=tails.min_n.astype(str)
dataset('remaining_bias',tails,['outputs/group_bias/threshold_counts.csv'],'Count of overlapping unique-member groups beyond ±5% after division by main-cohort mean; descriptive, not independent tests.')
dataset('existing_gains',gains,['outputs/conditional/performance_gains.csv'],'Existing spatial/forward calibration MSE gains and fixed-prediction spatial-cluster bootstrap intervals.')

a=slopes.iloc[0]; u=slopes.iloc[1]; m=slopes.iloc[2]
main_scores=scores.query("cohort=='main' and scheme=='spatial'").set_index('model')
prose('summary', '''## 研究结论 / Research summary

**已有数据支持：低价成交住宅的相对估值更高，且部分组合的偏差不能用全样本统一偏移概括。** 这是对保留交易样本的观察性结论。它还没有证明某个学校、治安指标或房屋特征造成了估价误差。

**复杂的组合值得研究，但复杂模型的收益并不自动成立。** 当前最有用的成果是可复查的异常组、条件对照和有限的预测改善。下一步应验证少量稳定组合是否在新时期仍成立，而不是继续用组数量充当证据强度。

The retained sales show a price-related assessment gradient and residual group differences. These are observational findings. Candidate interactions deserve follow-up; reliable improvements to an assessment system still require independent validation.

[打开完整交互工作台 / Open the workbench](./index.html#view=overview) · [查看最高／最低组 / Group extremes](./index.html#view=extremes) · [下载本页统计与复算脚本 / Reproducible results](./research-story-sources.zip)
''')
prose('question','''## 01 · 回到原问题：低价房是否被相对高估？ / The original question

最初交接文档研究的是估值累退性：低价住宅是否以成交价的更高比例被估值。它要求一个清楚的主关系、正式检验、重复成交检查和结论。后来的组合研究用于追问“偏差集中在哪些条件”，两者在这里接起来。

用 **P 表示成交价，A 表示源估值，q=P/A**。q=100% 是两者一致；q>100% 表示成交高于估值；q<100% 表示估值高于成交。组指标为 **q̄G=Σ(Pi/Ai)/nG**。这延续你的排序口径。最初文档采用反方向 A/P；二者逐笔互为倒数，组平均不能直接取倒数转换。

2017清洗样本有 **8,595笔**；组合主样本 **4,903笔（57.0%）**；正车库样本 **2,148笔（25.0%）**，后两者有重叠，不能相加。信息可得性与价格相关，因此组合结论不能外推至全部交易或全市未成交住宅。

The question concerns assessment levels relative to observed sale prices, not an unobserved true value. The narrative uses q=P/A; group rankings remain arithmetic means of transaction ratios.
''')
prose('gradient','''## 02 · 低价端更接近高估，但最高价端并非一路走高 / A gradient, not a monotone law

低于5万美元的496笔交易，中位q约 **90.47%**；20–30万美元的1,778笔约 **116.73%**。百万以上仅66笔，中位q回落至 **109.35%**。所以可以说低价端的相对估值更高，不能说“房子越贵就必然越低估”。

下图每个点代表一个价格档的中位数，横轴为不等宽价格区间，100%横线表示一致。它直观展示现象，但价格同时出现在分组和q的分子中，成交噪声可能放大梯度；需要下面的金额关系、比例性与去重对照。

The lowest band has a lower median sale/assessment ratio. The top band reverses part of the rise and is small. Shared-price coupling means this chart alone cannot establish regressivity.
''','price_bands')
chart('bands-chart','价格档的成交／估值 / Sale-to-assessment by price band','line','价格档 / Price band','中位比率 % / Median q','price_bands',reference=100)
prose('correlation',f'''## 03 · r 很高，不等于估得准 / Correlation is not calibration

在全部2017交易中，金额的 Pearson **r={a.pearson:.4f}**；log金额的 **r={a.log_pearson:.4f}**。含截距简单回归 log(A)~log(P) 的样本内 **R²={a.ols_r2:.4f}**。这些数字说明两种金额通常一起增减，不能解释为“{a.ols_r2:.1%}的房屋估准了”。

**r=Cov(P,A)/(sd(P)sd(A))** 描述线性共同变化；**R²=1−Σ(y−ŷ)²/Σ(y−ȳ)²** 描述相对于常数均值的平方误差减少。只有同样本、含截距的一元OLS中，R²才等于相应r的平方。

估值是否成比例，要看 **log(A)=α+βlog(P)+ε** 的β是否等于1；完全一致还要求相应截距与水平正确。即使每套房A都等于0.8P，相关系数仍可为1。这个代数例子解释为什么高r不能排除系统偏差。

High price correlation measures co-movement. Calibration asks whether the levels and slope agree with equality. In-sample log-price R² is not out-of-sample bias prediction accuracy.
''','proportionality')
prose('inference',f'''## 04 · 比例性偏离明显；当年没有重复房屋 / Proportionality and unique parcels

全部2017交易的 **β={a.beta:.4f}，95%参考区间 [{a.ci_low:.4f}, {a.ci_high:.4f}]**。按房屋编号聚类，对H₀:β=1做双侧检验：**t={a.t:.2f}，df={int(a.df):,}，p={a.p_value:.2e}**。这与“高价端估值增加得较慢”的样本模式一致。

2017的8,595笔恰好对应8,595个不同房屋编号，按房屋去重仍为 **{int(u.n):,}套**，β不变；这是确认当年没有重复权重，不是另一次独立验证。主组合样本改用 **{int(m.clusters)}个2km网格聚类**，β为 **{m.beta:.4f}**。下表给出区间与统计量，比较不同误差相关性假设下的结果；这些是不同样本的敏感性对照，不能当作嵌套因果模型。

**这个很小的p值不消除选择偏误或年份疑问。** 区间使用CR1聚类协方差与t(G−1)参考分布；全样本仅处理同房屋的相关性，网格检查也不能保证消除跨网格相关。成交测量误差仍可影响β。已有数据被多轮查看，本轮检验应称为探索性的条件推断，不能包装为事前注册的验证。

The conditional slope differs from one. All 2017 retained parcel IDs are unique, so deduplication changes nothing. Cluster-based intervals address specified dependence only; source selection, timing and transaction measurement error remain unresolved.
''','proportionality')
table('slopes-table','比例性与重复成交对照 / Proportionality and repeat-sales sensitivity','proportionality',
      [('sample','样本 / Sample','text'),('n','n','number'),('beta','β','number'),('ci_low','95%下界 / Lower','number'),('ci_high','95%上界 / Upper','number'),('t','t: β=1','number'),('clusters','聚类数 / Clusters','number')])
prose('groups','''## 05 · 整体偏移之外，确实还剩组合差异 / Group differences remain after a common shift

主组合样本整体均比率约108.40%。如果统一除去这一水平偏移，**至少100笔的组仍有46,350个超出±5%**；至少300笔时有931个，至少500笔时有51个；至少1,000笔时为0个。这比直接数“超过105%的组”更能区别共同偏移与局部差异。

下图改变组内最少交易数，数的是重叠的不同成员组。大量组可能反复包含同一批房屋：46,350组不是46,350次独立发现。原始均值的高低排序和所有条件表达的直方图仍在完整工作台中保留。

After a common level adjustment, group deviations remain at moderate sample sizes. Increasing minimum group size reduces their count. Overlapping groups are not independent evidence units.
''','remaining_bias')
chart('tails-chart','统一校准后仍超出±5%的组数 / Groups beyond ±5% after common calibration','bar','最少交易数 / Minimum n','groups','remaining_bias',reference=0)
prose('interaction','''## 06 · 联合效应用“差的差”描述 / Describe interaction as a difference of differences

把两个条件A、B各分成两档，四格均比率记为μ₀₀、μ₁₀、μ₀₁、μ₁₁。**ΔAB=μ₁₁−μ₁₀−μ₀₁+μ₀₀**：它衡量“A的差异在B改变后又改变了多少”。Δ=0符合这四格的加性关系；偏离0提示统计交互。四格成员不同，仍不是改变同一房屋条件后的因果效应。

已有一个卧室×周边制造业岗位占比的主样本例子，原始Δ约−8.26个百分点，加性残差Δ约−9.73个百分点。部分空间单元很稀疏，因此它适合作为验证候选。你关心的更高阶关系可用 **ΔS=ΣT⊆S(−1)^(|S|−|T|)μT** 延伸；各格须明确共同基准及非空支持，不能用任意不同参照的组均值混算。

另一个组M025有325笔，均比率114.17%；放宽其入室盗窃记录档位后，新增562笔均值106.04%，原始差8.14个百分点。共同支持只留下117与280笔，联合标准化后差为6.82个百分点。这说明已测量条件的组成没有消除该比较中的差异；它不证明治安是原因。

[四格交互与可查编号 / Inspect interaction cells](./index.html#view=interactions) · [M025完整条件 / Inspect M025](./index.html#view=controls&group=main-03600322)

Difference-of-differences expresses non-additivity; standardization checks measured composition on common support. Neither alone identifies a causal mechanism.
''')
four=cells.loc[cells.label.eq('I1')].copy()
four['卧室档 / Bedrooms']=four.cell.astype(str).str.zfill(2).str[0].map({'0':'1–2','1':'3'})
four['制造业岗位占比 / Manufacturing share']=four.cell.astype(str).str.zfill(2).str[1].map({'0':'>0–2.439%','1':'>7.874%'})
four['组均比率 % / Mean q']=four.mean_ratio*100
assert np.isclose(four.mean_ratio.iloc[3]-four.mean_ratio.iloc[2]-four.mean_ratio.iloc[1]+four.mean_ratio.iloc[0],-.0826215049011302)
dataset('four_cells',four,['outputs/conditional/四格组均值_Four_Cell_Means.csv'],'I1 four observed cell means and n; lines join different groups, not repeated observations or causal effects.')
prose('four-reading','''两条线若平行，卧室档位的差异在这两个周边就业档相同；现在两线的斜率不同，对应−8.26个百分点的原始交互。四格分别只有41、65、229、315笔，这张图表达的是已选中的探索线索，不能把线段当成同一房屋的变化轨迹。制造业档位是周边岗位构成，不是具体公司的因果效应。

Non-parallel lines visualize the observed interaction. Each endpoint represents a different group; the small cells and prior selection limit inference.''','four_cells')
chart('four-cell-chart','卧室×周边岗位构成 / Bedrooms × local employment mix','line','卧室档 / Bedrooms','组均比率 % / Mean q','four_cells',color='制造业岗位占比 / Manufacturing share',reference=100)
prose('prediction',f'''## 07 · 解释价格很容易，预测偏差仍难 / Predicting bias is the harder task

这次从保存的空间折外预测补算了真正以 **q=P/A为目标** 的R²。主样本的加性模型为 **{main_scores.loc['additive','r2']:.4f}**，交互模型为 **{main_scores.loc['interaction','r2']:.4f}**。它们只解释了较少的q变动，远低于前面log金额的样本内R²；两者预测目标和验证方式不同，不能互相比成同一个模型的进步。

下图只比较同一主样本的空间折外q预测，基准分母为这4,903笔q围绕自身均值的总平方差。R²可为负，表示不如该评估样本的常数均值；这个均值只是评分参照，不是训练时使用的预测值。

Direct spatial out-of-fold R² targets transaction q. The interaction model is slightly better on this direct squared-error metric; most transaction-level ratio variation remains unexplained.
''','prediction_scores')
score_chart=scores.query("cohort=='main' and scheme=='spatial'")[['model','r2']].copy()
score_chart['model']=score_chart.model.map({'original':'原估值 / Original','global':'统一水平 / Global','additive':'加性 / Additive','interaction':'交互 / Interaction'})
dataset('q_r2_chart',score_chart,['outputs/research_story/prediction_scores.csv'],'Main-cohort spatial OOF R² of direct q predictions, same 4903 observations and SST.')
chart('q-r2','对成交／估值的折外预测 / Out-of-fold prediction of q','bar','model','r2','q_r2_chart',reference=0)
prose('gain','''## 08 · 能否改善估价，要看另一个具体目标 / Improvement depends on the loss function

旧研究的校准后指标计算 **q′=P/(A·q̂)**，看q′偏离1的均方误差。相对统一水平校准，主样本加性模型减少误差 **3.44%（内部参考区间0.71%至6.19%）**，交互模型为 **3.00%（−0.59%至6.42%）**。因此不能说交互在这项校准目标上更好；这与它的直接q预测R²稍高并不矛盾。

**正车库样本给出负结果：** 空间验证下交互校准的误差改善为−6.21%，即误差增加。下一阶段不能只展示主样本表现好的指标。主样本加性模型的时间留后检验参考区间也跨过零，不能把空间结果当成稳定的跨期收益。上面区间是固定已有预测的空间聚类重抽样，未重新拟合或重做全部筛选，不是新数据确认，也不是两个模型收益差的直接区间。

Calibration loss and direct-q prediction loss weight errors differently. Keep both objectives visible. The garage-cohort deterioration argues against deploying a complex correction on the current evidence.
''','existing_gains')
prose('algebra','''## 09 · 数亿个组可以压缩；压缩不是机制证明 / Compression is not explanation

主样本落在3,310个有数据的完整条件格。保存每格交易数n与比率和s，任意组都能精确计算 **q̄G=(1ᵀDGs)/(1ᵀDGn)**。这就是将巨大组目录变成两个稀疏向量与一个选择运算；没有必要逐个组重新建模。

已有多项式核表示的主样本秩从常数阶1升至一阶96、二阶2,156、三阶3,310。三阶在这些观察点上满秩，因而可以精确重建现有组均值。**它没有证明现实只存在三阶关系，也没有证明这些系数能预测新房屋。** 正确结论是：我们找到了一种当前有限样本的精确表示。

[查看阶数、误差与矩阵 / Explore the algebra](./index.html#view=algebra)

The sparse count/sum representation is exact on observed support. Full rank at degree three is a finite-sample interpolation result, not a maximum causal interaction order.
''')
prose('conclusion','''## 10 · 现在能下什么结论，下一步怎样让它更强 / Conclusions and the next study

**对原问题的回答：** 已有2017交易样本支持低价端相对估值更高的模式；比例性检验提供佐证，当年没有重复房屋权重。不是所有低价房都高估，最高价端也不是单调更低估。

**对扩展问题的回答：** 整体水平校准之外存在可复查的组合差异，部分在共同支持与已测条件标准化后仍保留；因此值得针对组合检查估价模型。现阶段不能确定偏差由哪一项现实特征造成，更不能说已优于政府现行模型或发现了前人从未发现的机制。

建议下一轮按以下顺序推进：

1. **关闭估值时间与上游筛选问题。** 原分母与官方2017估值并非全部一致；先固定可审计的成交—估值时点口径，重建筛选过程。保留原结果作为敏感性对照。
2. **冻结少量候选组合，再收新时期数据。** 选择有效交易多、空间分布较广、去重后稳定、条件可解释的组合；事先固定切点、效应方向、最低支持和主要损失函数。以房屋和地区处理依赖，报告效应量、区间与多重比较控制。
3. **直接比较简单校准、加性、交互模型。** 同一训练／测试样本、同一目标，报告整体误差和低价／高价组校准，检查是否改善一组却恶化另一组。把“有交互”与“加入交互可改善预测”当作不同假设。
4. **补总体代表性证据。** 在历史全体房屋清单可取得时，按共同估值档比较成交率与信息覆盖率；目前不能靠给可用样本加权就假装已解决不可观测选择。

值得继续回答的是：年份口径修正后这些组合还在吗？同一条件在不同区域／时期方向一致吗？异常主要来自遗漏质量、模型形式还是成交与记录过程？这三类问题决定本研究能从“发现线索”前进到何种强度的结论。

The next study should freeze candidate definitions, resolve timing and source filters, validate on a new period, compare losses on identical samples, and audit sold-versus-unsold representation. These steps connect a useful exploratory result to an actionable assessment-model evaluation.
''')

sources.extend([
    dict(id='initial-brief',label='Original research brief',path='Property_Tax_Assessment_Project_Agent_Handoff.docx',sha256=sha(handoff)),
    dict(id='controls-evidence',label='Saved conditional comparisons and four-cell results',path='outputs/conditional/report_summary.json',inputFiles=['outputs/conditional/四格组均值_Four_Cell_Means.csv','outputs/group_bias/report_summary.json','outputs/group_bias/standardization.csv']),
    dict(id='algebra-evidence',label='Observed-support kernel ranks',path='outputs/group_algebra/main_orders.csv'),
    dict(id='scope-evidence',label='Cohort and denominator audit',path='outputs/conditional/source_scope.csv')])
for block in blocks:
    if block['id']=='interaction':block['sourceId']='controls-evidence'
    if block['id']=='algebra':block['sourceId']='algebra-evidence'
title='Philadelphia Assessment Bias — Research Story'
artifact=dict(surface='report',manifest=dict(version=1,surface='report',title=title,
    description='研究主线：结论、统计证据与下一步 / Findings, evidence and next steps',generatedAt=STAMP,
    blocks=blocks,charts=charts,tables=tables,sources=sources),
    snapshot=dict(version=1,generatedAt=STAMP,status='ready',datasets=datasets),sources=sources)
(OUT/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
(OUT/'research_story.md').write_text('\n\n'.join(markdown),encoding='utf-8')
db.close()
assert all(sha(ROOT/name)==digest for name,digest in INPUTS.items())
validation=dict(status='passed',inputs_unchanged=INPUTS,initial_brief_sha256=sha(handoff),
    checks=['Pearson log-r squared equals simple OLS R²','Independent QR influence-form CR1 covariance agrees',
    'Saved-prediction calibration RMSE reconciles to existing performance','Latest sale per parcel deterministic',
    'All original input hashes unchanged'],new_statistics=slopes.to_dict(orient='records'),r_execution='not yet run')
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
print(slopes.to_string(index=False))
print(main_scores[['r2','calibrated_ratio_rmse']].to_string())
