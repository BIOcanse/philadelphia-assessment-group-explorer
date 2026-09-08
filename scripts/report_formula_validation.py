"""Extend the existing research story with measured validation of its own formula."""
from pathlib import Path
from datetime import datetime,timezone
import copy
import json
import sqlite3
import hashlib
import pandas as pd
import numpy as np
from query_group_means import Groups

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'outputs/formula_validation'
OUT=ROOT/'outputs/formula_validation_report';OUT.mkdir(exist_ok=True)
base=json.loads((ROOT/'outputs/research_overview/artifact.json').read_text())
artifact=copy.deepcopy(base);manifest=artifact['manifest'];datasets=artifact['snapshot']['datasets']
stamp=datetime.now(timezone.utc).isoformat();manifest['generatedAt']=stamp;artifact['snapshot']['generatedAt']=stamp
manifest['title']='Group Bias, a Formula, and Its First Hold-out Test'
manifest['description']='研究主线与公式实测 / Research findings and validation of the derivation'
sources=manifest['sources'];blocks=manifest['blocks'];charts=manifest['charts'];tables=manifest['tables']
HASHES={};db=sqlite3.connect(OUT/'report_source.sqlite')

def read(name):
    path=ROOT/name;HASHES[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text()) if path.suffix=='.json' else pd.read_csv(path)

results=read('outputs/formula_validation/metrics.csv');cases=read('outputs/formula_validation/cases.csv')
synthetic=read('outputs/formula_validation/synthetic/metrics.csv');coverage=read('outputs/formula_validation/coverage.csv')
validation=read('outputs/formula_validation/validation.json');assert validation['status']=='passed'
catalog=pd.concat([read(f'outputs/formula_validation/{c}_catalog_metrics.csv') for c in ['main','positive_garage']])
catalog_counts={c:read(f'outputs/formula_validation/{c}_catalog_summary.json') for c in ['main','positive_garage']}
for name in ['docs/formula_validation.md','docs/formula_validation_results.md','scripts/formula_validation.py',
             'scripts/validate_formula_validation.py','scripts/scan_formula_groups.cpp','scripts/scan_formula_groups.py']:
    HASHES[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
COHORT={'main':'主样本 / Main','positive_garage':'正车库 / Positive garage'}
MODEL={'constant':'训练均值 / Constant','additive':'固定一阶 / Additive',
       'original_k3':'原无正则三阶 / Original k3','selected':'训练内选阶 / Selected degree'}

def source(id,label,paths,description):
    sources[:]=[s for s in sources if s['id']!=id]
    sources.append(dict(id=id,label=label,path=paths[0],inputFiles=paths,description=description,
        sha256={p:HASHES[p] for p in paths if p in HASHES}))

def data(id,frame,paths,description):
    frame.to_csv(OUT/(id+'.csv'),index=False)
    frame.to_sql(id,db,if_exists='replace',index=False)
    datasets[id]=json.loads(frame.to_json(orient='records',force_ascii=False))
    source(id,description,[f'outputs/formula_validation_report/{id}.csv',*paths],description)
    sources[-1]['query']=dict(engine='SQLite',language='sql',sql=f'SELECT * FROM "{id}";',tables_used=[id],description=description)

def prose(id,body,source_id='formula-study'):
    return dict(id=id,type='markdown',body=body,layout='full',sourceId=source_id)

def replace(id,body,source_id='formula-study'):
    i=next(i for i,b in enumerate(blocks) if b['id']==id);blocks[i]=prose(id,body,source_id)

def chart(id,title,kind,dataset,x,y,color=None,reference=None):
    encoding={'x':{'field':x,'type':'quantitative' if kind in ['line','scatter'] else 'ordinal'},'y':{'field':y,'type':'quantitative'}}
    if color:encoding['color']={'field':color,'type':'nominal'}
    item=dict(id=id,title=title,type=kind,dataset=dataset,sourceId=dataset,layout='full',encodings=encoding,
        xAxisTitle=x,yAxisTitle=y,valueFormat='number',settings={'sort':'none','showPoints':'always'},maxRows=300)
    if reference is not None:item['referenceLines']=[dict(axis='y',value=reference,label=str(reference),lineStyle='dashed',color='neutral')]
    charts.append(item)
    return dict(id=id+'-block',type='chart',chartId=id,layout='full')

def table(id,title,dataset,columns):
    tables.append(dict(id=id,title=title,dataset=dataset,sourceId=dataset,layout='full',density='spacious',
        columns=[dict(field=f,label=label,format=fmt) for f,label,fmt in columns],defaultSort={'field':columns[0][0],'direction':'asc'}))
    return dict(id=id+'-block',type='table',tableId=id,layout='full')

source('formula-study','Executed validation of the original kernel derivation',
       ['docs/formula_validation.md','outputs/formula_validation/metrics.csv','outputs/formula_validation/validation.json'],
       '30 internal real-data experiments; train-only profile fitting and degree selection; fixed historical bins; group-mean target.')
source('known-truth','Controlled known-answer experiments',['outputs/formula_validation/synthetic/metrics.csv'],
       'Synthetic eight-field functions; 256 profiles, 4 independent test repeats per profile; complete and unseen support; not housing observations.')
source('interpretation','Research decisions after the executed tests',['docs/formula_validation_results.md'],
       'Evidence-based interpretation and next-stage questions; regularization is proposed, not yet evaluated.')

primary=results[results.order.eq(1)&results.minimum_n.eq(30)]
fixed=primary[primary.kind.eq('random')&primary.seed.eq(20260908)&primary.fraction.eq(1)]
def result(cohort,model):return fixed[fixed.cohort.eq(cohort)&fixed.model.eq(model)].iloc[0]
main=result('main','additive');k3=result('main','original_k3')
assert abs(main.r2-.508423)<1e-6 and abs(k3.r2+.424697)<1e-6
replace('summary',f'''## 当前结论 / Research summary

**我们现在已有本公式的真实留出验证：现有条件包含一定可预测的组间结构，但原来的无正则三阶精确表达没有表现出稳定的预测优势。**

主样本以3,943笔训练、960笔留出，在预设的74个单字段条件组上，固定一阶公式 **r={main.r:.3f}、预测R²={main.r2:.3f}、RMSE={main.rmse_pp:.2f}个百分点**；原三阶R²={k3.r2:.3f}。这些分数来自我们自己的核公式和相同测试成员，不是其他模型或金额相关性。

已知答案实验验证了核与显式方程的一致性，也显示：当支持允许识别时，四阶关系能被恢复；缺少组合状态或存在噪声时，精确拟合并不保证准确延拓。**下一步重点是检验怎样稳定地保留联合规律，而不是继续追求训练内零误差。**

The derivation now has measured hold-out results. Additive structure predicts some group differences, while the original unregularized degree-three interpolant lacks stable predictive advantage. Controlled tests support the mathematics and expose support/noise limitations.

[完整工作台 / Full workbench](./index.html#view=overview) · [本轮数据、方程与验证记录 / Evidence and equations](./research-story-sources.zip)
''')
replace('inventory','''## 03 · 从发现与表达，推进到方法实测 / What we have completed

我们已经完成数据整理、任意组合发现、条件比较和数学表达。本轮再完成30项真实数据实验与180项已知答案设置，将“方程如何从部分资料推导出来”整个过程放到留出数据上检查。下表标明各项工作的证据角色。

The study now includes actual validation of the derivation. Discovery, representation, predictive tests and mechanism interpretation remain distinct stages.
''')
ledger=pd.DataFrame(datasets['research_ledger'])
ledger.loc[ledger['order'].eq('05'),'completed']='已执行30项真实数据实验与180项合成设置 / 30 real-data cases and 180 synthetic settings'
ledger.loc[ledger['order'].eq('05'),'meaning']='已有训练外成绩；泛化受范围和选阶稳定性约束 / Held-out evidence with scope and selection limits'
data('research_ledger',ledger,['docs/formula_validation_results.md'],'Current research inventory; formula validation executed in this version.')
for b in blocks:
    if b['id']=='formula':
        b['body']=b['body'].replace('公式解决了表达问题，预测能力尚待检验 / The formula has a verified representation role',
            '先分清表达与预测，再读实测结果 / Representation and prediction have separate tests')
    if b['id']=='unit':b['body']=b['body'].replace('接下来的组预测也按同一单位评价','本轮组预测按同一单位评价')

score_table=fixed.copy()
score_table['cohort_label']=score_table.cohort.map(COHORT);score_table['model_label']=score_table.model.map(MODEL)
data('formula_scores',score_table,['outputs/formula_validation/metrics.csv'],
     'Fixed random holdout, first prespecified seed. Single-field partitions, held-out n >= 30. Training-selected degree is one specified run, not the best test seed.')
new=[]
new.append(prose('validation','''## 07 · 评分对象是重新推导的方程 / What exactly was tested

每次只在训练交易中重新构造剖面、计算均值并求系数；测试成员只接受预测。**主指标比较同一组测试成员的实际q平均与预测平均。** 单字段类别构成互斥分区；每个有效分区权重相同，区内合格组等权。主样本74组、正车库54组，每组测试n≥30。不同分区会重复使用交易，这些组不是独立重复样本。

下表比较预先固定的训练均值、一阶、原三阶，以及只用训练内部数据从全部0..20/21阶中选出的方程。显示第一预设种子；三种子完整结果与选阶敏感性在后文。r描述共同变化，预测R²按平方误差定义，可以为负；常数预测的r为空。百分点误差给出实际偏离量。

Each equation is derived using training responses only. Scores compare predicted and observed means on identical held-out members. These are retrospective internal tests with an already explored feature dictionary, not untouched external confirmation or pre-sale forecasting.
'''))
new.append(table('formula-score-table','固定留出组指标 / Fixed hold-out group scores','formula_scores',
    [('cohort_label','样本 / Cohort','text'),('model_label','公式 / Formula','text'),('degree','阶数 / Degree','number'),
     ('r','r','number'),('r2','预测 R²','number'),('rmse_pp','RMSE · pp','number'),('groups','组数 / Groups','number')]))

new.append(prose('learning','''## 08 · 训练量增加并未消除选阶波动 / Learning and degree selection

以下曲线在同一批测试成员上，使用10%、25%、50%、100%的可用训练交易重新推导。每点是三个预设种子的误差中位数；完整最小值/最大值保留在源表中。种子改变训练抽样和内部选阶，不改变外层测试集；这不是三个独立外部重复。

主样本使用全部3,943笔时，三个内部选阶结果为8、17、1，对应测试R²约0.187、0.162、0.508；正车库为21、0、21。选择过程会波动，因此不能只展示表现最好的一次。固定三阶的训练剖面误差接近0，留出误差仍高，这与单交易剖面多、插值对噪声敏感相容，尚不能归因于某一个具体原因。

The learning curves reveal instability in selected complexity. Full training interpolation is compatible with substantial held-out error. The displayed medians are descriptive; all seed outcomes remain available.
'''))
learning=primary[primary.kind.eq('random')].groupby(['cohort','model','fraction','train_n'],as_index=False).agg(
    rmse_pp=('rmse_pp','median'),rmse_min=('rmse_pp','min'),rmse_max=('rmse_pp','max'),r2=('r2','median'),r2_min=('r2','min'),r2_max=('r2','max'))
learning['Formula / 公式']=learning.model.map(MODEL);learning['训练笔数 / Training rows']=learning.train_n
learning['组均误差 / RMSE · pp']=learning.rmse_pp
for cohort in ['main','positive_garage']:
    subset=learning[learning.cohort.eq(cohort)].copy()
    data('learning_'+cohort,subset,['outputs/formula_validation/metrics.csv'],'Same fixed test groups across four training sizes; medians over three training/selection seeds; min/max retained.')
    new.append(chart('learning-'+cohort,COHORT[cohort]+' · 学习曲线 / Learning curve','line','learning_'+cohort,
        '训练笔数 / Training rows','组均误差 / RMSE · pp','Formula / 公式'))
    if cohort=='main':new.append(prose('learning-garage-note','''正车库样本在小训练量下更不稳定，增加训练资料后也没有显示稳定的联合阶数优势。它是主样本的选择子集；两条曲线的差别不能解释为车库变量的效果。

The positive-garage cohort is smaller and selected. Its learning pattern is not an isolated estimate of the garage feature's value.
'''))

new.append(prose('all-groups','''## 09 · 任意阶组目录也接受了留出检查 / The complete group directory

我们重新计算了全部7,598,906个已有条件组的测试成员，而不只检验单字段组。主样本有482,261个原组没有测试成员；其余组按测试成员精确去重后，得到831,185个不同测试成员组，正车库为264,935个。以下表格按测试支持n≥30/100分别列出；去重仍不消除组间重叠。

主样本n≥30的132,602组，一阶r约0.750、R²约0.376、RMSE约2.48个百分点；原三阶R²约−0.261。可见一阶结构的信号不只出现在单字段评分中，但任意组合上的误差更大，仍留下需要研究的联合差异。不要把这与前表74组的R²混成同一口径。

All existing groups were evaluated on their held-out members, with exact membership duplicates removed for this table. The broader group family has different dispersion and weighting from the primary partitions. Neither millions of group rows nor deduplication creates independent evidence.
'''))
cat=catalog[catalog.basis.eq('unique_test_members')&catalog.minimum_n.isin([30,100])&catalog.model.isin(['additive','original_k3','selected'])].copy()
cat['cohort_label']=cat.cohort.map(COHORT);cat['model_label']=cat.model.map(MODEL)
data('catalog_scores',cat,[f'outputs/formula_validation/{c}_catalog_metrics.csv' for c in COHORT],
    'First prespecified full-development model; all supported arbitrary-order original conditions; exact held-out-member deduplication; remaining overlaps are not independent.')
new.append(table('catalog-table','任意阶测试成员组 / All-order test-member groups','catalog_scores',
    [('cohort_label','样本 / Cohort','text'),('minimum_n','测试 n≥','number'),('model_label','公式 / Formula','text'),
     ('groups','组数 / Groups','number'),('r','r','number'),('r2','预测 R²','number'),('rmse_pp','RMSE · pp','number')]))

new.append(prose('transfer','''## 10 · 新组合、地区与时间给出不同边界 / Transfer within the current data

新增三种完整重训：全部剖面分组留出、1公里网格分组留出、成交日期最后约20%留出。同一天不跨时间边界；内部选阶也采用对应类型的划分。网格留出没有空间缓冲，时间测试仍在2017年内。

下图只展示训练内选阶规则的结果，完整基准对照保留在来源数据。主样本在三种划分上的R²分别约0.412、0.183、0.298；正车库更弱。原无正则三阶在两样本三种划分中的R²均为负。这里已经有可重复结构的线索，但并没有得到一套在所有范围都可靠的联合公式。

Profile, grid and chronological holdouts answer different transfer questions. Main-cohort selected equations show positive results in these specified tests, but performance and selected degree depend on scope. This is within-dataset transfer, not new-year or new-city confirmation.
'''))
transfer=primary[primary.kind.ne('random')&primary.model.eq('selected')].copy()
transfer['样本 / Cohort']=transfer.cohort.map(COHORT)
transfer['划分 / Holdout']=transfer.kind.map({'profile':'未见完整组合 / Unseen profile','spatial':'空间网格 / Spatial grid','time':'较晚成交 / Later dates'})
transfer['预测 R²']=transfer.r2
data('transfer_scores',transfer,['outputs/formula_validation/metrics.csv','outputs/formula_validation/cases.csv'],
    'Separate internal transfer cases, train-only matched inner splitting; primary single-field partitions, test n >= 30; baseline cases are retained in the full source tables.')
new.append(chart('transfer-chart','训练内选阶的迁移指标 / Selected-rule transfer scores','bar','transfer_scores','划分 / Holdout','预测 R²','样本 / Cohort',0))

new.append(prose('synthetic','''## 11 · 已知答案解释了为什么“精确”仍可能不准 / What known-answer tests establish

我们构造了8个二值字段的256个状态，分别设定单项、两项、四项、八项关系与纯噪声，共180个阶数/支持/噪声设置。这里按完整状态评分，每状态有4个独立测试重复；不套用住房n≥30门槛，也不以单字段均值判断高阶奇偶关系。

下图是无噪声四阶函数。使用205个状态训练，在51个未见状态上，四阶真值误差约4.3×10⁻¹³个百分点，三阶约10.66、八阶约4.51。四阶空间在这批训练支持上足以识别该函数；更宽的空间仍能精确拟合训练值，却选择了不同延拓。

加入标准差4个百分点的独立噪声后，四阶未见状态真值RMSE约4.04个百分点；完整支持下约1.56。八阶奇偶关系在缺角支持上也未恢复。**数学等价性、可辨识性和噪声稳定性是三项不同的检验。** 这些是受控示例，不是现实房价函数的证明。

Controlled tests verify equivalence and identifiable recovery, while exposing extrapolation and noise limits. Higher degrees are not universally better. Error against the known function and error against noisy test means are saved separately.
''','known-truth'))
syn=synthetic[synthetic.signal.eq('four_way')&synthetic.noise_pp.eq(0)].copy()
syn['支持 / Support']=syn.support.map({'complete':'完整支持 / Complete','unseen':'未见状态 / Unseen'})
syn['允许阶数 / Degree']=syn.degree;syn['真值误差 / RMSE · pp']=syn.truth_rmse_pp
data('known_four_way',syn,['outputs/formula_validation/synthetic/metrics.csv'],
    'Synthetic noise-free four-way function on 256 eight-bit states; full-state group means. 205 training/51 unseen states in the unseen case.')
new.append(chart('synthetic-chart','四阶已知函数的状态预测误差 / Known four-way function errors','line','known_four_way',
    '允许阶数 / Degree','真值误差 / RMSE · pp','支持 / Support',0))

new.append(prose('residuals','''## 12 · 将预测误差重新连接到具体条件 / Residuals remain inspectable

下图每点为主样本一个预设单字段测试组，显示第一预设种子的选阶公式。横轴是实际组均成交／估值百分比，纵轴是预测减实际的百分点误差；0线表示一致。每个点的条件名称与支持规模保留在图表数据中，因此数字能回到具体组别。

这些残差用于下一步诊断，不能把按测试误差挑出的组再当作未筛选的确认结果。来源包还保留任意阶组的最大残差及正式组号，可返回原工作台查看完整条件。

Residuals identify where the selected equation misses the specified held-out group means. Post-test extreme residuals are exploratory diagnostics, not independently confirmed mechanisms.
'''))
scatter=pd.read_csv(INPUT/'main/random-20260908-100/groups.csv')
scatter=scatter[scatter.model.eq('selected')&scatter.order.eq(1)].copy()
group_catalog=Groups('main')
scatter['group_id']=[group_catalog.lookup(group_catalog.condition_ids(codes.split()))['group_id'] for codes in scatter.condition_codes]
scatter['实际均比率 / Observed mean · %']=100*scatter.actual
scatter['预测误差 / Prediction error · pp']=100*(scatter.predicted-scatter.actual)
data('group_residuals',scatter,['outputs/formula_validation/main/random-20260908-100/groups.csv'],
    '74 primary main-cohort test groups, n >= 30; first prespecified selected-degree model; full condition descriptions and support retained.')
new.append(chart('residual-chart','组均值与预测误差 / Group means and prediction errors','scatter','group_residuals',
    '实际均比率 / Observed mean · %','预测误差 / Prediction error · pp',reference=0))
worst=pd.read_csv(INPUT/'main_catalog_worst.csv').iloc[:2]
links=[]
for row in worst.itertuples():
    title=row.conditions.replace('"',"'")
    links.append(f'[{row.group_id}](./index.html#group={row.group_id} "{title}")（测试n={row.test_n}，预测误差{row.error_pp:+.2f}个百分点）')
new.append(prose('residual-links','按第一预设选阶模型的测试误差选出的核查例子：'+'；'.join(links)+
    '。悬停编号可见原条件，点击返回完整组；工作台显示的是原全样本统计，本页误差使用留出成员。\n\nThese examples are selected after examining test residuals. IDs resolve to the original full-cohort groups; the validation statistics use held-out members.'))

new.append(prose('next','''## 下一步 · 检验联合项能否带来稳定增益 / The next research decision

当前证据支持继续研究，但研究目标应从“精确保存当前数据”转向“稳定学习组合规律”。下一步保留同一条件核和任意阶能力，比较明确的谱收缩/正则化与更稳定的训练内选阶，检验联合项相对单项是否带来可重复增益。它们尚未在本轮执行，不能提前写成提升。

之后才依据稳定残差决定具体补充哪些现实资料，并评价校准后的估价差距。真正确认泛化需要兼容新时期数据；现有选择样本和时间信息的限制仍然有效。预测成功也不自动给出政府估价偏差的因果来源。

Next, test whether controlled shrinkage and more stable training-only selection preserve useful joint structure beyond the additive baseline. Mechanism investigation and valuation improvement require their own evidence; external confirmation needs aligned new data.
''','interpretation'))
new.append(prose('conclusion','''## 阶段结论 / Where the study now stands

**已完成：** 组合差异发现、统一数学表达，以及本推导方法的实际留出和已知答案检验。主样本存在可预测的组间结构；原无正则三阶的精确还原没有转化为稳定的预测优势。

**仍未解决：** 怎样稳定地提取联合项、怎样进一步压缩为可读规律，以及这些规律对应哪些现实原因。当前结果既没有否定联合偏差存在，也没有证明复杂公式越高阶越有效。

The study has advanced from representation to empirical validation. There is predictive group structure, and there is a concrete stability problem to solve before treating a complex expression as a reusable valuation-bias model.
''','interpretation'))
blocks[:]=[b for b in blocks if b['id'] not in ['validation','next','conclusion']]+new
artifact['sources']=sources
for id,rows in datasets.items():
    if not (OUT/(id+'.csv')).exists():pd.DataFrame(rows).to_csv(OUT/(id+'.csv'),index=False)
db.close()
for source,sha in validation['source_hashes'].items():assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==sha,source
(OUT/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
(OUT/'research_story.md').write_text('\n\n'.join(b['body'] for b in blocks if b['type']=='markdown'),encoding='utf-8')
(OUT/'validation.json').write_text(json.dumps(dict(status='passed',new_analysis=True,formula_holdout_validation='executed',
    experiment_cases=30,synthetic_settings=180,source_hashes=HASHES,original_inputs_unchanged=True,
    independent_validation='outputs/formula_validation/validation.json',charts=len(charts),tables=len(tables)),indent=2),encoding='utf-8')
print(json.dumps(dict(status='built',blocks=len(blocks),charts=len(charts),tables=len(tables))))
