"""Add the executed individual-training study to the preserved research narrative."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
import hashlib
import sqlite3
import numpy as np
import pandas as pd
from raw_feature_formula import ROOT, OUT as INPUT, ROLES
from query_group_means import Groups

OUT = ROOT / 'outputs/raw_feature_formula_report'; OUT.mkdir(exist_ok=True)
artifact = copy.deepcopy(json.loads((ROOT / 'outputs/formula_validation_report/artifact.json').read_text('utf-8')))
manifest = artifact['manifest']; datasets = artifact['snapshot']['datasets']
blocks = manifest['blocks']; sources = manifest['sources']; charts = manifest['charts']; tables = manifest['tables']
stamp = datetime.now(timezone.utc).isoformat()
manifest.update(title='From Individual Transactions to Group Predictions',
                description='逐笔学习、连续信息与组均值验证 / Individual training and held-out group validation', generatedAt=stamp)
artifact['snapshot']['generatedAt'] = stamp
validation = json.loads((INPUT / 'validation.json').read_text()); assert validation['status'] == 'passed'
db = sqlite3.connect(OUT / 'report_source.sqlite'); hashes = dict(validation['source_hashes'])
results = pd.read_csv(INPUT / 'metrics.csv'); rows = pd.read_csv(INPUT / 'row_metrics.csv')
cases = pd.read_csv(INPUT / 'cases.csv')
catalog = pd.concat([pd.read_csv(INPUT / (c+'_catalog_metrics.csv')) for c in ['main', 'positive_garage']])
MODEL = dict(constant='训练均值 / Constant', bins_group='分档·组选模 / Bins–group',
             bins_row='分档·逐笔选模 / Bins–row', raw_group='连续·组选模 / Raw–group',
             raw_row='连续·逐笔选模 / Raw–row', bins_additive='分档加性 / Binned additive',
             raw_additive='连续加性 / Raw additive')
COHORT = dict(main='主样本 / Main', positive_garage='正车库 / Garage')
fixed = results[results.kind.eq('random')&results.seed.eq(20260908)&results.fraction.eq(1)&results.minimum_n.eq(30)]
fixed_rows = rows[rows.kind.eq('random')&rows.seed.eq(20260908)&rows.fraction.eq(1)]
cat = catalog[catalog.basis.eq('unique_test_members')&catalog.minimum_n.eq(30)]


def score(cohort, model, order=1):
    return fixed[fixed.cohort.eq(cohort)&fixed.model.eq(model)&fixed.order.eq(order)].iloc[0]


def cat_score(cohort, model):
    return cat[cat.cohort.eq(cohort)&cat.model.eq(model)].iloc[0]


def prose(id, body, source='raw-study'):
    return dict(id=id, type='markdown', body=body, layout='full', sourceId=source)


def source(id, label, paths, description):
    for path in paths:
        hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    sources.append(dict(id=id, label=label, path=paths[0], inputFiles=paths,
                        sha256={p: hashes[p] for p in paths}, description=description))


def data(id, frame, paths, description):
    frame.to_csv(OUT / (id+'.csv'), index=False)
    frame.to_sql(id, db, if_exists='replace', index=False)
    datasets[id] = json.loads(frame.to_json(orient='records', force_ascii=False))
    source(id, description, [f'outputs/raw_feature_formula_report/{id}.csv', *paths], description)
    sources[-1]['query'] = dict(engine='SQLite', language='sql', sql=f'SELECT * FROM "{id}";',
        tables_used=[id], description=description)


def chart(id, title, kind, dataset, x, y, color=None):
    enc = {'x': dict(field=x, type='quantitative' if kind in ['line', 'scatter'] else 'ordinal'),
           'y': dict(field=y, type='quantitative')}
    if color:
        enc['color'] = dict(field=color, type='nominal')
    charts.append(dict(id=id, title=title, type=kind, dataset=dataset, sourceId=dataset, layout='full',
        encodings=enc, xAxisTitle=x, yAxisTitle=y, valueFormat='number',
        settings=dict(sort='none', showPoints='always'), maxRows=500,
        referenceLines=[dict(axis='y', value=0, label='0', lineStyle='dashed', color='neutral')]))
    return dict(id=id+'-block', type='chart', chartId=id, layout='full')


def table(id, title, dataset, columns):
    tables.append(dict(id=id, title=title, dataset=dataset, sourceId=dataset, layout='full', density='spacious',
        columns=[dict(field=f, label=label, format=fmt) for f, label, fmt in columns],
        defaultSort=dict(field=columns[0][0], direction='asc')))
    return dict(id=id+'-block', type='table', tableId=id, layout='full')


source('raw-study', 'Frozen individual-training experiment and independent checks',
       ['docs/raw_feature_formula.md', 'outputs/raw_feature_formula/validation.json',
        'outputs/raw_feature_formula/metrics.csv', 'outputs/raw_feature_formula/row_metrics.csv'],
       '18 matched retrospective internal cases, continuous/binned features, individual/marginal selectors; unchanged cohorts.')
source('raw-catalog', 'All-order held-out group audit',
       ['outputs/raw_feature_formula/main_catalog_metrics.csv', 'outputs/raw_feature_formula/positive_garage_catalog_metrics.csv',
        'outputs/raw_feature_formula/main_catalog_summary.json', 'outputs/raw_feature_formula/positive_garage_catalog_summary.json'],
       'Complete original catalog; exact held-out membership deduplication; individual prediction sums within frozen binned profiles.')

m = score('main', 'raw_row'); ma = score('main', 'raw_additive')
m2 = score('main', 'raw_row', 2); ma2 = score('main', 'raw_additive', 2)
mc = cat_score('main', 'raw_row'); mac = cat_score('main', 'raw_additive')
mr = fixed_rows[fixed_rows.cohort.eq('main')&fixed_rows.model.eq('raw_row')].iloc[0]
gr = score('positive_garage', 'raw_row'); gc = cat_score('positive_garage', 'raw_row')
paired = results[results.order.eq(2)&results.minimum_n.eq(30)].pivot(index=['cohort', 'case'], columns='model', values='rmse_pp')
wins = int((paired.raw_row < paired.raw_additive-1e-10).sum())
ties = int((abs(paired.raw_row-paired.raw_additive) <= 1e-10).sum())

current = [prose('summary', f'''## 当前结论 · 训练对象改到逐笔之后，规律仍然只有部分可预测 / Current finding

**这轮已经跑完：18套相同划分的对照、逐笔学习与选模、连续变量、正则化，以及任意阶组目录验证。仍未得到“小部分样本学会、对其余样本优秀拟合”的公式。**

主样本用3,943笔训练、960笔留出：逐笔预测R²={mr.r2:.3f}；单变量组R²={m.r2:.3f}；双变量组R²={m2.r2:.3f}；任意阶组R²={mc.r2:.3f}。这些是不同粒度的指标，不能混为一个准确率。组评分均要求至少30笔留出交易；单/双变量还要求每个分区至少两个合格组。

联合流程在18套双变量组比较中有{wins}套误差更低、{ties}套相同，显示进一步研究的价值；但改进幅度有限，也还没有不确定性检验来确认稳定优势。下面先讲本轮结果；此前研究完整保留在后半部分。返回[完整研究工作台](./index.html#view=overview)，或下载[方程、预测和审计来源包](./research-story-sources.zip)。

The completed comparison finds partial predictive structure, not a recovered universal law. Individual R² and group-mean R² answer different questions. Earlier analyses remain available below and in the workbench.
''')]

current.append(prose('raw-method', '''## A · 这次究竟改了什么 / What changed

每笔房屋的目标始终是 qᵢ=成交价ᵢ／原估值ᵢ。**用训练交易学习公式 → 对未参与训练的交易逐笔预测 → 按原条件分组 → 比较预测均值和实际均值。** 不用成交价格或价格档作为预测变量。

原方法将“所有分档条件完全相同”的记录合并，并按记录数加权，其平方误差拟合已经与逐笔训练等价。本轮真正改变的是：保留连续数值、允许正则化，以及用逐笔验证误差选模型；同一候选池也按旧的单变量组误差选一次，形成对照。

两个样本、原20/21个字段和原划分都保留。小训练量为开发池50%：主样本1,972笔、车库858笔；大训练量为3,943/1,717笔。每种训练量用三个种子，另做完整组合、空间网格和内部时间留出，总共18套。现有测试结果早已被查看过，因此这是**内部回顾验证**，不是新的盲测。

Training uses individuals; evaluation aggregates only held-out predictions and outcomes over identical group members. The old identical-profile compression was loss-equivalent. This study tests feature resolution, regularization and selection, with matched splits and no new exclusions.
'''))
current.append(prose('raw-equation', '''## B · 现在得到的矩阵与方程 / The fitted equation

**α=(K+nλI)⁻¹(q−μ)，q̂(x)=μ+k(x,X)ᵀα。** μ为训练成交比率均值，λ是只在训练内部选择的正则化强度。保存的NPZ包含α、训练点、标准化参数及所有核参数，可以重新逐笔计算预测。

每个字段先形成相似度 bⱼ：连续变量用高斯相似度，邮编用是否同类。加性核为 Kₐ=Σⱼbⱼ/d；联合核为 Kⱼ=∏ⱼ(1+τbⱼ)/(1+τ)ᵈ。后者等于 **Σₛ τ^|S|∏ⱼ∈ₛbⱼ/(1+τ)ᵈ**，S遍历包括空集在内的全部字段子集。因此一阶直到20/21阶都在表达中，计算不需要逐项展开数百万组合。

但各阶权重受到这个核的结构约束，λ控制拟合复杂度。允许全部阶数不等于已经识别出必须存在的20阶作用。加性对照允许单变量弯曲关系；它不是只画一条直线的弱基准。

The saved kernel-ridge equation includes all interaction orders through a product expansion. It is a structured, regularized family, not an unrestricted proof of the true interaction order. The additive comparator allows nonlinear single-feature functions.
'''))

equations = []
for cohort in COHORT:
    meta = json.loads((INPUT / cohort / 'random-20260908-100/case.json').read_text())
    for role in ['raw_row', 'raw_additive']:
        d = meta['selected'][role]
        equations.append(dict(cohort=COHORT[cohort], model=MODEL[role], family=d['family'],
                              tau=d['tau'], ell=d['ell'], penalty=f"λ = {d['penalty']:.0e}"))
data('raw_equations', pd.DataFrame(equations), ['outputs/raw_feature_formula/main/random-20260908-100/case.json',
     'outputs/raw_feature_formula/positive_garage/random-20260908-100/case.json'],
     'Selected seed-08 full-development equations; parameters chosen on inner validation only.')
current.append(table('raw-equations-table', '可重算的参数 / Recomputable parameters', 'raw_equations',
    [('cohort', '样本 / Cohort', 'text'), ('model', '公式 / Formula', 'text'), ('family', '核 / Kernel', 'text'),
     ('tau', 'τ', 'number'), ('ell', 'ℓ', 'number'), ('penalty', 'λ', 'text')]))

current.append(prose('raw-comparison', f'''## C · 更细的信息有没有带来提升 / Did the changes help?

下表将“分档／连续”与“组误差／逐笔误差选模”分开，所有行使用同一固定留出成员。逐笔误差以百分点计；R²是1−预测平方误差／实际组均值方差，越高越好，负值意味着比直接用测试均值还差。

主样本连续逐笔选模的单变量组 r={m.r:.3f}，R²={m.r2:.3f}，RMSE={m.rmse_pp:.2f}个百分点；双变量组R²={m2.r2:.3f}。同样连续输入的加性对照分别为{ma.r2:.3f}和{ma2.r2:.3f}。**对照的差异有限，不能宣称已经抓到了此前遗漏的大量高阶规律。**

Compare both calibration and correlation. A higher r alone does not establish a better equation. These pipeline comparisons also change applicable similarity functions and candidate grids; they do not isolate binning as a causal treatment.
'''))
comparison = []
for cohort in COHORT:
    for role in ['bins_group', 'bins_row', 'raw_group', 'raw_row', 'raw_additive', 'bins_additive']:
        r = fixed_rows[fixed_rows.cohort.eq(cohort)&fixed_rows.model.eq(role)].iloc[0]
        comparison.append(dict(cohort=COHORT[cohort], model=MODEL[role], row_rmse=r.rmse_pp,
            single_r2=score(cohort, role).r2, pair_r2=score(cohort, role, 2).r2,
            all_r2=cat_score(cohort, role).r2))
data('raw_comparison', pd.DataFrame(comparison), ['outputs/raw_feature_formula/metrics.csv',
     'outputs/raw_feature_formula/row_metrics.csv', 'outputs/raw_feature_formula/main_catalog_metrics.csv',
     'outputs/raw_feature_formula/positive_garage_catalog_metrics.csv'],
     'Fixed seed-08, full-development fits. Original binned group definitions; arbitrary-order groups deduplicated by test members.')
current.append(table('raw-comparison-table', '同成员对照 / Matched holdout comparison', 'raw_comparison',
    [('cohort', '样本 / Cohort', 'text'), ('model', '流程 / Pipeline', 'text'),
     ('row_rmse', '逐笔RMSE · pp', 'number'), ('single_r2', '单变量组 R²', 'number'),
     ('pair_r2', '双变量组 R²', 'number'), ('all_r2', '任意阶组 R²', 'number')]))

bars = []
for role in ['bins_additive', 'raw_additive', 'raw_row']:
    for level, val in [('单变量 / Single', score('main', role).r2),
                       ('双变量 / Pair', score('main', role, 2).r2), ('任意阶 / All orders', cat_score('main', role).r2)]:
        bars.append({'组族 / Group family': level, '预测 R²': val, '公式 / Formula': MODEL[role]})
data('raw_family_scores', pd.DataFrame(bars), ['outputs/raw_feature_formula/metrics.csv',
     'outputs/raw_feature_formula/main_catalog_metrics.csv'], 'Main cohort, same test transactions; separate group families, n>=30.')
current.append(chart('raw-family-chart', '联合公式与加性公式 / Joint-capable and additive equations',
                     'bar', 'raw_family_scores', '组族 / Group family', '预测 R²', '公式 / Formula'))

learning = results[results.cohort.eq('main')&results.kind.eq('random')&results.order.eq(2)&results.minimum_n.eq(30)&
                   results.model.isin(['raw_row', 'raw_additive', 'bins_additive'])]
curve = learning.groupby(['train_n', 'model'], sort=True).r2.agg(['mean', 'min', 'max']).reset_index()
curve['训练交易数 / Training n'] = curve.train_n; curve['平均预测 R²'] = curve['mean']; curve['公式 / Formula'] = curve.model.map(MODEL)
data('raw_learning', curve, ['outputs/raw_feature_formula/metrics.csv'],
     'Main pair-group R2, n>=30; mean and full range over three seeds sharing the same test set, not confidence intervals.')
current.append(prose('raw-learning', f'''## D · 数据加倍后是否更稳定 / Learning and transfer

下图把主样本训练量从1,972增加到3,943笔，始终预测相同960笔留出交易的双变量组均值。蓝线为分档加性，棕线为连续加性，绿线为允许联合项的连续逐笔流程。线为三个种子的均值，来源表保留最小值、最大值；它们共享测试集，不能当作三份独立证据。

合计18套比较中，“允许联合项并按逐笔选模”的双变量组误差低于连续加性对照的有{wins}套，数值相同{ties}套，其余更高。选到加性时，两者本来就是同一个模型；选到联合核也不能直接推出作用阶数。改善是否稳定，比某一套里谁略胜更重要。

Learning curves use held-out outcomes only. Seed variation is sensitivity to training and selection, not a confidence interval or independent replication.
'''))
current.append(chart('raw-learning-chart', '增加训练数据后的双变量组预测 / Pair-group learning curve',
    'line', 'raw_learning', '训练交易数 / Training n', '平均预测 R²', '公式 / Formula'))
transfer = results[results.kind.ne('random')&results.order.eq(2)&results.minimum_n.eq(30)&results.model.isin(['bins_additive', 'raw_additive', 'raw_row'])].copy()
transfer['_model_order'] = transfer.model.map({'bins_additive': 0, 'raw_additive': 1, 'raw_row': 2})
transfer = transfer.sort_values(['cohort', 'kind', '_model_order']).drop(columns='_model_order')
transfer['样本 / Cohort'] = transfer.cohort.map(COHORT); transfer['公式 / Formula'] = transfer.model.map(MODEL)
transfer['留出 / Holdout'] = transfer.kind.map(dict(profile='未见组合 / Profile', spatial='空间网格 / Spatial', time='较晚成交 / Time'))
transfer['预测 R²'] = transfer.r2
data('raw_transfer', transfer, ['outputs/raw_feature_formula/metrics.csv'],
     'Main and garage pair-group metrics, test n>=30; profile, grid and within-2017 chronological transfer. No spatial buffer.')
data('raw_transfer_main', transfer[transfer.cohort.eq('main')], ['outputs/raw_feature_formula/metrics.csv'],
     'Main-cohort transfer comparison; shared model selection rules and matched inner split types.')
current.append(chart('raw-transfer-chart', '主样本的组合、地区和时间迁移 / Main-cohort transfer',
    'bar', 'raw_transfer_main', '留出 / Holdout', '预测 R²', '公式 / Formula'))
current.append(table('raw-transfer-table', '两种样本的迁移结果 / Both cohorts', 'raw_transfer',
    [('样本 / Cohort', '样本 / Cohort', 'text'), ('留出 / Holdout', '留出 / Holdout', 'text'),
     ('公式 / Formula', '公式 / Formula', 'text'), ('r2', '双变量组 R²', 'number'), ('rmse_pp', 'RMSE · pp', 'number')]))

worst = pd.read_csv(INPUT / 'main_catalog_worst.csv')
scatter = pd.read_csv(INPUT / 'main/random-20260908-100/groups.csv')
scatter = scatter[scatter.model.eq('raw_row')&scatter.order.eq(1)].copy()
g = Groups('main')
scatter['group_id'] = [g.lookup(g.condition_ids(codes.split()))['group_id'] for codes in scatter.condition_codes]
scatter['实际组均 / Observed mean · %'] = 100*scatter.actual
scatter['实际偏离100% / Observed bias · pp'] = 100*(scatter.actual-1)
scatter['预测误差 / Error · pp'] = 100*(scatter.predicted-scatter.actual)
data('raw_residuals', scatter, ['outputs/raw_feature_formula/main/random-20260908-100/groups.csv'],
     'Each point is an original single-field group using only test members; group IDs refer to full-cohort catalog entries.')
current.append(prose('raw-groups', f'''## E · 最后仍然回到具体组 / Return to identifiable groups

任意阶目录重新检查了7,598,906个正式组。去除空测试组并按测试成员去重后，n≥30的主样本组有132,602个、车库组45,285个；它们仍然大量重叠。连续逐笔选模在这两批组上的R²分别为{mc.r2:.3f}、{gc.r2:.3f}。

下图每个点为一个主样本单变量留出组，横轴为实际成交／估值组均相对100%的偏离（百分点），纵轴为预测误差（百分点）。横轴+10表示组均比率110%。悬停数据可查条件，下面的正式组号还可直接返回原工作台。编号相同，但工作台的完整组统计与这里的留出成员统计有不同分母。

The complete catalog is evaluated by summing individual predictions, including variation within old bins. Overlapping group counts are descriptive coverage, not independent sample sizes.
''', 'raw-catalog'))
current.append(chart('raw-residual-chart', '哪些条件仍预测不准 / Remaining group residuals',
                     'scatter', 'raw_residuals', '实际偏离100% / Observed bias · pp', '预测误差 / Error · pp'))
group_links = pd.concat([pd.DataFrame(datasets['group_links']),
    scatter[['group_id', 'conditions']], worst[['group_id', 'conditions']]]).drop_duplicates('group_id')
sources[:] = [s for s in sources if s['id'] != 'group_links']
data('group_links', group_links, ['outputs/formula_validation_report/group_links.csv',
    'outputs/raw_feature_formula/main/random-20260908-100/groups.csv', 'outputs/raw_feature_formula/main_catalog_worst.csv'],
    'Original and current canonical group IDs with source-backed full conditions; hints do not change prediction membership.')
link_text = '；'.join(f'[{r.group_id}](./index.html#group={r.group_id})（测试n={r.test_n}，误差{r.error_pp:+.2f}个百分点）'
                     for r in worst.head(2).itertuples())
current.append(prose('raw-group-links', '本轮按任意阶组测试误差选出的探索例子：'+link_text+
    '。悬停编号显示条件；这些组已按结果筛选，不能再视作独立确认。\n\nThese post-test residual examples are exploratory. Hover an ID for conditions; click for the original group.', 'raw-catalog'))
current.append(prose('raw-next', '''## 接下来该解决什么 / Next research decision

这轮排除了一个简单解释：问题并不只是“拿组均值训练”或“没有允许高阶”。保留连续信息、逐笔选模、允许全部阶数之后，仍没有出现全面优秀的留出拟合。当前证据不支持把一个模型直接称为真解。

下一步应固定这轮保存的预测，先分清**组均值本身的抽样波动有多大，剩余误差是否还有可重复结构**。用按房屋重采样的成对误差区间比较加性与联合公式；重叠组要一起随房屋重采样，不能把数十万组当成独立样本。再通过交叉拟合检查残差与联合条件的关系，诊断应与最终确认分开。

如果残差结构能复现，再针对性检验更灵活的核相似度、正则化选择或已有字段的语义问题，并用独立时期数据确认；如果没有，继续无目的扩大阶数并不能区分噪声和缺少信息。此次尚未执行上述不确定性与残差检验。

Next, quantify paired uncertainty by resampling transactions, then test whether residual structure repeats under cross-fitting. Preserve joint group membership in resampling. This determines whether another richer equation is warranted; it has not yet been executed.
'''))
current.append(prose('raw-scope', '''## 使用边界与核验 / Scope and verification

18套实验的划分、模型选择、保存方程逐笔重算以及组均值、r、R²均已核验。全阶扫描的交易数与原目录逐组一致，另对每个样本40个固定抽取的任意阶组直接重算成员；这40项是抽查，不声称独立逐组重算了全部预测。

单/双变量评分沿用旧规则：先要求组内最少交易数，再保留至少两个合格组的分区，分区等权、分区内组等权。全阶目录按独特测试成员组等权。两者不是同一指标。原楼层字段仍是语义有疑点的代理（主样本最大值52），未擅自裁剪为“正常楼层”。房屋属性快照、当前坐标代理、历史评分及估值年份口径等限制仍在；可得性与价格相关的样本结论不得推广到整体，更不能据预测相关性宣称因果来源。

Independent validation covers all stored predictions and supported group scores. Historical snapshots, feature semantics, selected-sample scope and previously inspected holdouts limit interpretation. No claim of causal identification or external validation is made.
'''))
current.append(prose('historical-boundary', '''## 前一阶段研究与证据 / Earlier research retained

以下是v1.4阶段的研究过程、无正则公式验证和已知答案实验。数字与原分析保持一致；其中“当前”“下一步”措辞以本页上方本轮结论为准。此前完整报告和方程证据也保留在下载包的previous_formula_evidence.zip中。

The following material preserves the preceding stage. Its historical status language is superseded by the new experiment above; its measured results are unchanged.
'''))
historical = [b for b in blocks if b['id'] not in ['summary', 'next', 'conclusion']]
blocks[:] = current + historical
artifact['sources'] = sources
for id, values in datasets.items():
    if not (OUT / (id+'.csv')).exists():
        pd.DataFrame(values).to_csv(OUT / (id+'.csv'), index=False)
db.close()
(OUT / 'artifact.json').write_text(json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
story = '\n\n'.join(b['body'] for b in current if b['type'] == 'markdown')
(OUT / 'research_story.md').write_text('\n\n'.join(b['body'] for b in blocks if b['type']=='markdown'), encoding='utf-8')
(ROOT / 'docs/raw_feature_formula_results.md').write_text(story, encoding='utf-8')
proof = dict(status='passed', formula_holdout_validation='executed: 18 raw-feature matched cases',
             source_hashes=hashes, charts=len(charts), tables=len(tables), blocks=len(blocks),
             independent_validation='outputs/raw_feature_formula/validation.json', old_results_preserved=True,
             note='Detailed report uses old runtime by design; no app migration or mobile changes.')
(OUT / 'validation.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(status='built', charts=len(charts), tables=len(tables), blocks=len(blocks)), ensure_ascii=False))
