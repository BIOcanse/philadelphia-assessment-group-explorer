"""Rebuild the research introduction from existing evidence, without new experiments."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/research_overview'
OUT.mkdir(exist_ok=True)
STAMP=datetime.now(timezone.utc).isoformat()
HASHES={}

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    p=ROOT/name;HASHES[name]=digest(p)
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.suffix=='.json' else pd.read_csv(p)

bias=read('outputs/group_bias/report_summary.json')
thresholds=read('outputs/group_bias/threshold_counts.csv')
scope=read('outputs/conditional/source_scope.csv')
orders={c:read(f'outputs/group_algebra/{c}_orders.csv') for c in ['main','positive_garage']}
summaries={c:read(f'outputs/group_algebra/{c}_summary.json') for c in orders}
registry=read('outputs/group_workbench/registry.json')
metadata=read('outputs/group_means/main.input.json')
for name in ['docs/group_algebra.md','docs/group_mean_ranking.md','docs/group_bias_followup.md',
             'docs/selection_bias_policy.md','docs/research_framework.md']:
    HASHES[name]=digest(ROOT/name)
focal=bias['focal_joint']
labels=[]
for term in focal['original_codes'].split():
    field,code=term.split('=')
    atom=next(a for a in metadata['atoms'] if a['name']==field and a['category']==int(code))
    labels.append(atom['label'])
group_description='；'.join(labels)

blocks=[];charts=[];tables=[];datasets={};sources=[];markdown=[]
db=sqlite3.connect(OUT/'report_source.sqlite')

def source(id,label,paths,definition):
    sources.append(dict(id=id,label=label,path=paths[0],inputFiles=paths,description=definition,
        sha256={p:HASHES[p] for p in paths if p in HASHES}))

def prose(id,body,source_id=None):
    b=dict(id=id,type='markdown',body=body,layout='full')
    if source_id:b['sourceId']=source_id
    blocks.append(b);markdown.append(body)

def data(id,frame,paths,definition):
    frame.to_sql(id,db,if_exists='replace',index=False)
    assert len(pd.read_sql_query(f'SELECT * FROM "{id}";',db))==len(frame)
    datasets[id]=json.loads(frame.to_json(orient='records',force_ascii=False))
    frame.to_csv(OUT/f'{id}.csv',index=False)
    sources.append(dict(id=id,label=definition,path=f'outputs/research_overview/{id}.csv',inputFiles=paths,
        transformation='scripts/build_research_overview.py: reshapes existing saved results; no new model fitting.',
        query=dict(engine='SQLite / outputs/research_overview/report_source.sqlite',language='sql',
                   sql=f'SELECT * FROM "{id}";',tables_used=[id],description='Display query over sourced results. '+definition)))

def chart(id,title,kind,dataset,x,y,color=None,reference=None):
    enc={'x':{'field':x,'type':'ordinal'},'y':{'field':y,'type':'quantitative'}}
    if color:enc['color']={'field':color,'type':'nominal'}
    c=dict(id=id,title=title,type=kind,dataset=dataset,sourceId=dataset,layout='full',encodings=enc,
           xAxisTitle=x,yAxisTitle=y,valueFormat='number',settings={'sort':'none','showPoints':'always'},maxRows=100)
    if reference is not None:c['referenceLines']=[dict(axis='y',value=reference,label=str(reference),lineStyle='dashed',color='neutral')]
    charts.append(c);blocks.append(dict(id=id+'-block',type='chart',chartId=id,layout='full'))

def table(id,title,dataset,cols):
    tables.append(dict(id=id,title=title,dataset=dataset,sourceId=dataset,layout='full',density='spacious',
        defaultSort={'field':cols[0][0],'direction':'asc'},columns=[dict(field=f,label=l,format=t) for f,l,t in cols]))
    blocks.append(dict(id=id+'-block',type='table',tableId=id,layout='full'))

source('framework','Research questions and next-stage plan',['docs/research_framework.md'],
       'Authored synthesis of the existing research, not experimental results. Formula holdout validation is not yet executed.')
source('scope','Cohort scope and selection',['outputs/conditional/source_scope.csv','docs/selection_bias_policy.md'],
       '2017 retained sales and available-feature cohorts; overlapping, selected cohorts; no citywide extrapolation.')
source('algebra','Exact representation and its limits',['docs/group_algebra.md','outputs/group_algebra/main_orders.csv',
       'outputs/group_algebra/positive_garage_orders.csv'], 'Existing weighted projections and support-rank results; not held-out prediction.')
source('focal','Existing common-support comparison',['outputs/group_bias/report_summary.json','outputs/group_means/main.input.json'],
       'M025 joint standardization; actual condition labels decoded from original atoms; observational comparison.')

ledger=pd.DataFrame([
    ['01','数据与适用范围 / Data and scope','清洗、历史信息关联、时间与可得性审计 / Cleaning, enrichment, timing and coverage audits','明确哪些记录可研究；未证明代表全市 / Defines the retained sample, not citywide representativeness'],
    ['02','寻找组合偏差 / Discover groups','任意阶枚举、组均排序、边缘组、重叠和规模检查 / Enumeration, means, extremes, overlap and support','定位有差异的条件组 / Locates observed group differences'],
    ['03','比较联合关系 / Compare joint patterns','条件放宽、标准化、四格比较 / Relaxations, standardization and four-cell contrasts','部分差异未被已有对照消除；原因未确认 / Residual associations, mechanism unconfirmed'],
    ['04','推导统一表达 / Derive a common expression','稀疏统计、选择算子、任意阶核、逐组还原 / Sparse statistics, operators, kernels and reconstruction','已验证有限样本表达 / Verified on observed support'],
    ['05','检查方法泛化 / Validate the derivation method','验证对象与步骤已明确；实验尚未执行 / Defined, not yet executed','当前没有本公式的留出r或R² / No held-out formula score yet'],
    ['06','形成可复查研究 / Make the study inspectable','组号、双语释义、图表、两版工作台 / IDs, labels, charts and both editions','可追溯、可阅读、可复算 / Traceable and reproducible']
],columns=['order','work','completed','meaning'])
data('research_ledger',ledger,['docs/research_framework.md'],'Evidence inventory; the formula-validation row explicitly marks unexecuted work.')
tails=thresholds.loc[thresholds.cohort.eq('main') & thresholds.basis.eq('global_scaled') & thresholds.min_n.isin([100,300,500,1000])]
tails=tails.groupby('min_n',as_index=False).agg(groups=('biased_groups','sum'),eligible=('eligible_groups','max'))
tails['组内最少交易数 / Minimum n']=tails.min_n.map(lambda n:f'n ≥ {n:,}')
tails['占合格组比例 % / Share of eligible groups']=100*tails.groups/tails.eligible
assert tails.groups.tolist()==[46350,931,51,0]
data('group_support',tails,['outputs/group_bias/threshold_counts.csv'],
     'Main-cohort overlapping unique-member groups beyond ±5% after division by the cohort mean. No independent-test interpretation.')
control=pd.DataFrame({'比较范围 / Comparison':['原始两组 / Original','共同支持 / Common support','共同支持并标准化 / Standardized'],
    '组均差，百分点 / Gap, pp':[focal['raw_gap_pp'],focal['common_gap_pp'],focal['standardized_gap_pp']],
    'n_A':[325,117,117],'n_B':[562,280,280]})
data('conditional_example',control,['outputs/group_bias/report_summary.json'],'M025 comparison: changing support and weights, not a causal attribution.')
rank_rows=[]
for c,o in orders.items():
    for row in o.itertuples():
        rank_rows.append({'允许阶数 / Maximum order':str(row.degree),'样本 / Cohort':'主样本 / Main' if c=='main' else '正车库 / Garage',
                         '现有剖面维度覆盖 % / Observed dimension coverage':100*row.rank/row.profiles,
                         'rank':row.rank,'profiles':row.profiles})
data('representation',pd.DataFrame(rank_rows),['outputs/group_algebra/main_orders.csv','outputs/group_algebra/positive_garage_orders.csv'],
     'Numerical rank / observed profiles in the nested categorical spaces; not accuracy, variance explained or predictive R².')

prose('summary','''## 当前结论 / Research summary

**我们已经完成“发现组合差异”和“把全部组均值写成统一表达”。现在要检验的是：这种推导方法能否从部分数据学出公式，预测未参与推导的数据中的组均值。**

这是本研究下一阶段的主问题。已有样本中的差异、数学上的精确还原、训练外预测和现实原因解释，各自需要相应证据。目前前两项已完成，后两项仍需检验。

We have mapped observed group differences and built an exact representation of group means. The next question is whether the derivation method can learn from part of the data and predict group means in held-out records. Reconstruction, generalization and causal explanation are separate evidence stages.

[完整工作台 / Full workbench](./index.html#view=overview) · [成果与研究方案 / Evidence and research plan](./research-story-sources.zip)
''','framework')
prose('question','''## 01 · 研究已经从“哪里估偏了”走到“能否推导出规律” / The question we are pursuing

现实出发点是：住宅的原估值与实际成交之间，是否存在有规律的组间偏差？我们逐步把单一价格档扩展为房屋、位置、学校、警情与岗位环境等条件的任意组合，寻找哪些组合的平均比例最高或最低。

随后出现一个方法问题：大量组彼此重叠，单项效应加起来未必等于联合结果。**能否把这种复杂结构组织为一个方程，并检验产生方程的方法是否可靠？** 这使研究形成一条连续主线：

**定位组合差异 → 推导统一表达 → 验证推导方法 → 提炼稳定规律 → 评价解释与应用价值。**

最初的公平性问题提供现实意义；公式及其验证是当前研究核心。最终可能帮助发现需要修正的估价环节，但现阶段尚未证明优于政府系统，也没有建立具体因果来源。

The practical question concerns assessment gaps. The methodological question is whether a unified formula can recover repeatable structure across combinations. Application follows evidence of generalization; it is not implied by a matrix representation alone.
''','framework')
prose('unit','''## 02 · 研究单位一直是条件组 / Our unit is a condition group

每笔交易的比例为 **q=成交价／原估值**。组指标是该组每笔q的算术平均：100%表示均比率与一致基准相同，超过100%表示成交相对估值更高。我们排序和验证的重点是组均值。

2017清洗基准有8,595笔；补充条件齐备的主组合样本有4,903笔、20个字段，正车库样本有2,148笔、21个字段。两个样本有重叠。资料可得性与价格有关，所以组合结论限相应可用交易，不自动代表全部交易或全市住宅。

接下来的组预测也按同一单位评价：对未参与推导的成员计算公式预测，再汇总为各组平均，与该组的实际平均比较。单套房预测仅作辅助检查。

We study arithmetic means of transaction-level sale/assessment ratios. The enriched cohorts are selected and overlap. Formula validation must compare predicted and observed means for the same held-out group members.
''','scope')
prose('inventory','''## 03 · 已经搭好了研究基础，缺口集中在公式验证 / What the completed work gives us

前期工作已经提供数据、候选组、联合关系、数学表达和复查工具。下表按它们在研究中的作用整理，而不是按脚本或执行日期列清单。**最大的缺口并非再多算一批组，而是把公式放到未参与推导的数据上检验。**

The completed work supplies the inputs, observed patterns, mathematical representation and inspection tools. The central missing evidence is held-out validation of the derivation method itself.
''','framework')
table('inventory-table','成果及其证据作用 / Completed work and evidence roles','research_ledger',
      [('order','顺序 / Step','text'),('work','工作 / Work','text'),('completed','目前做到什么 / Current state','text'),('meaning','能支持什么 / Meaning','text')])
prose('discovery','''## 04 · 部分组差异超出共同水平偏移 / Differences extend beyond one common offset

主样本共有5,550,736个不同成员条件组，整体均比率约108.40%。在统一除去这一水平偏移后，至少100笔的组仍有46,350个偏离±5%；至少300笔有931个，至少500笔有51个，至少1,000笔则为0个。

下图显示不同支持门槛下，这些组占合格组的比例。它说明差异并非只发生在个位数小组中，同时也显示大支持规模下差异收窄。**这些组高度重叠，不能把组数量当作独立发现数量。** 排序提供候选，重复出现的规律仍须另行验证。

Some group differences remain after a common level adjustment. Their prevalence falls as the minimum group size increases. Counts refer to overlapping groups, not independent discoveries.

[查看原始高低组、条件和分布 / Inspect extremes and conditions](./index.html#view=extremes)
''')
chart('support-chart','共同水平校准后的组差异 / Group differences after common calibration','bar','group_support',
      '组内最少交易数 / Minimum n','占合格组比例 % / Share of eligible groups',reference=0)
prose('comparison',f'''## 05 · 联合条件值得研究，但现有对照尚未给出原因 / Joint conditions matter; mechanism remains open

我们已经做过条件放宽、共同支持标准化和四格非加性比较。一个可复查的例子是 [M025的完整条件](./index.html#view=controls&group=main-03600322 "{group_description}")：

**{group_description}。**

放宽其中的住宅入室记录条件后，原325笔与新增562笔的组均差为8.14个百分点。进入共同支持后只保留117与280笔；联合标准化后仍差6.82个百分点。下图把支持改变与标准化后的结果并列，说明已测条件的组成没有消除这个比较中的差异。

它没有隔离出治安的因果作用。全1,920项标准化比较中，653项有共同支持，1,267项无法计算；这些未成功的比较也构成研究结论。现有控制分析的价值是缩小问题范围，并识别哪些解释还缺证据。

The M025 contrast remains on a smaller common-support sample after standardization. This is a conditional association. Many planned comparisons lack common support, so the existing controls do not settle the causal mechanism.
''','focal')
chart('comparison-chart','一个组对照的差距变化 / An existing group contrast','bar','conditional_example',
      '比较范围 / Comparison','组均差，百分点 / Gap, pp',reference=0)
prose('formula','''## 06 · 公式解决了表达问题，预测能力尚待检验 / The formula has a verified representation role

相同完整条件组合的交易会同时进入任何相关条件组。因此，每种完整状态只需保留**交易数n和比率和s**，就能重建全部组均值。主样本的5,550,736个组由3,310个有数据的完整状态支撑；这使庞大目录可以统一计算。

我们又构建了逐阶条件核，把状态均值写成 **m̂(x)=μ+ΣαᵤKₖ(x,xᵤ)**。条件核把单项、两项及更高阶组合放在同一套函数空间中；参数由数据求出。这套核与显式条件空间的等价性、数值计算和现有组还原已经核验。

下图展示允许阶数增加时，能表达的数值维度占已观察状态数的比例。两样本在三阶达到100%，意味着当前支持上可以精确插值。**这不是留出准确率，也不证明现实关系最高只有三阶。** 主样本仍保留3,310个系数，正车库1,449个；低阶表达与少参数规律还不是同一项成果。

The count/sum representation exactly recovers observed group means. The kernel gives a nested all-order function space. Full observed rank at degree three establishes interpolation on current support; it does not establish a small-parameter law or predictive accuracy.

[查看原方程、矩阵与还原误差 / Inspect the original algebra](./index.html#view=algebra)
''','algebra')
chart('representation-chart','阶数与已观察支持的表达维度 / Order and observed support rank','line','representation',
      '允许阶数 / Maximum order','现有剖面维度覆盖 % / Observed dimension coverage',color='样本 / Cohort',reference=100)
prose('validation','''## 07 · 现在要验证的是“如何得到公式”这整个过程 / Validate the derivation, end to end

**当前没有本核公式的训练外r或R²成绩。** 之前展示的金额相关系数与另一套梯度提升模型的成绩，各有其背景用途，都不属于本公式的验证。

下一阶段用现有数据就可以完成三个相连的检验：

1. **能不能从少量数据学到规律？** 用不同训练量重新构建状态、求参数并选择表达，在固定的留出记录上比较预测组均值。画出训练量与准确性的关系，并与共同均值、单项等简单方法比较。
2. **换一批组合或地区还成立吗？** 区分训练中见过和未见过的完整状态，再做空间与内部时间留出。某种划分成功，不能替代其他范围的证据。
3. **方法能否区分规律与噪声？** 复用已有已知四阶关系的反例，再扩展已知答案和噪声条件，检查何时可恢复、何时无法辨识。数学证明、可控实验和真实数据验证共同约束结论。

r说明预测与实际组均值是否同向变化；预测R²衡量相对于基准的平方误差，百分点误差说明实际差多少。它们都对应**本公式、同一测试组、同一批成员**。大批重叠组用于全面诊断；易读的主证据按预设分区及组规模分别展示，不能拿组行数当独立样本量。

当前分档和研究方向已经看过全量资料，因此这些是内部方法检验。其他年份虽有部分成交数据，但相应历史条件尚未齐备，真正跨期确认需要后续对齐。

Train the complete derivation on subsets, evaluate held-out group means, compare simple baselines, and test transfer and known-answer cases. Report r, predictive R² and errors for this formula and this target. Current resplits remain internal validation, not a pristine new confirmation sample.
''','framework')
prose('next','''## 08 · 先验证，再决定怎样简化与解释 / Let validation guide the next research choice

**第一优先级是公式验证。** 它将决定后续工作，而不是预先假定越高阶、矩阵越复杂越好。

- 如果较少数据已经能稳定预测留出组均值，就有依据继续寻找更少参数、可读的表达，再验证兼容新时期。
- 如果训练内精确、留出表现差，应检查推导步骤的稳定性、支持不足和复杂度，再在训练内部选择更合适的表达。
- 如果只在某些组规模、条件范围或地区成立，就报告这个适用范围，并研究成功与失败的组有什么差别。

这些结果出来后，再利用现有编号、条件对照和残差，把统计规律连接到具体房屋与环境。机制解释和校准收益各自检验；即使预测成功，也不能直接认定某项条件造成政府估价偏误。

更换模型、Transformer矩阵比较、扩展城市与继续抓取外部属性都可以保留为后续方向。当前已有数据足以先回答更关键的问题：**我们的推导方法是否学到了可以重复使用的组间关系？**

Validation determines the next branch: simplify a useful predictor, repair an unstable derivation, or state a restricted domain. Mechanism and policy application follow their own evidence. Additional model families and external collection need not precede this test.
''','framework')
prose('conclusion','''## 阶段结论 / Where the study stands

**已完成：** 可核查的数据基础、任意组合的组均差异发现、联合关系与条件对照、有限样本的统一代数表达，以及可复查的工作台。

**尚未完成的核心：** 从部分数据重新推导公式后，对未参与推导的组均值进行验证。当前既没有证据宣布这套方法已能外推，也不能借用其他模型的低分宣布它失败。

**接下来最值得做：** 以现有数据完成公式学习曲线和留出验证，再据结果决定简化、补充资料或机制研究。这会把项目从“观察和表示差异”推进到“检验是否存在可重复规律”。

The study has completed discovery and observed-data representation. Held-out validation of the derivation is the next decisive result. That result will guide simplification, new evidence collection and substantive interpretation.
''','framework')

artifact=dict(surface='report',manifest=dict(version=1,surface='report',title='From Group Differences to a Testable Formula',
    description='研究主线与阶段结论 / Research questions, evidence and next steps',generatedAt=STAMP,
    blocks=blocks,charts=charts,tables=tables,sources=sources),
    snapshot=dict(version=1,generatedAt=STAMP,status='ready',datasets=datasets),sources=sources)
(OUT/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
(OUT/'research_story.md').write_text('\n\n'.join(markdown),encoding='utf-8')
db.close()
assert all(digest(ROOT/p)==h for p,h in HASHES.items())
assert summaries['main']['profiles']==3310 and summaries['positive_garage']['profiles']==1449
assert all(int(o.iloc[-1]['rank'])==int(o.iloc[-1]['profiles']) for o in orders.values())
validation=dict(status='passed',source_hashes=HASHES,original_inputs_unchanged=True,
    formula_holdout_validation='not executed; no score supplied',new_analysis=False,
    checks=['Existing group support counts reconciled','Ranks and profile counts checked','M025 labels decoded from original atoms',
            'Old results preserved','No unrelated model score used as formula validation'],
    structure={'summary':'summary','question':'question','scope':'unit','evidence':'inventory/discovery/comparison/formula',
               'methods':'formula/validation','uncertainty':'adjacent to each finding','next_steps':'next','conclusion':'conclusion'},
    delivery='Canonical HTML through existing report pipeline; desktop workbench link unchanged.')
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'built','blocks':len(blocks),'charts':len(charts),'tables':len(tables),'formula_validation':'not executed'}))
