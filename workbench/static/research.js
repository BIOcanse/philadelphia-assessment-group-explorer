/* Shared research interface for the local API and independent browser Worker. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const e = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = v => Number(v).toLocaleString('en-US');
  const pct = v => v == null ? '—' : (100 * v).toFixed(2) + '%';
  const pp = v => v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2) + ' pp';
  const blue = '#3979ac', orange = '#c18445', gray = '#8996a2';
  const views = [['overview','研究总览','Overview'],['extremes','极端组','Group extremes'],['controls','条件对照','Comparisons'],['interactions','组合交互','Interactions'],['algebra','矩阵与方程','Algebra'],['validation','模型检验','Validation'],['coverage','数据与信源','Data & sources'],['directory','组目录','Group directory']];
  const S = {data:null,cohort:'main',view:'overview',exports:new Map(),cache:new Map(),hoverSerial:0,hoverTarget:null,minimum:100,degree:2,profileStart:0,comparison:null,interaction:null};
  const info = () => S.data.cohorts[S.cohort];
  const meta = () => S.data.metadata.cohorts.find(r => r.id === S.cohort);
  const label = field => meta().fields.find(f => f.name === field)?.label || field;
  function category(field, code, cohort=S.cohort) { const f = S.data.metadata.cohorts.find(c=>c.id===cohort).fields.find(f=>f.name===field); return f?.categories.find(c=>c.code===Number(code))?.label ?? String(code); }
  function conditions(codes,cohort=S.cohort) {
    const fields = S.data.metadata.cohorts.find(c=>c.id===cohort).fields;
    return codes ? codes.split(' ').map(code => {const [name,value]=code.split('=');const f=fields.find(f=>f.name===name);return (f?.label||name)+' = '+category(name,value,cohort);}) : ['全部固定样本 / Entire fixed cohort'];
  }
  function summary(id) {
    const row=S.data?.groups[id];
    if(row){const cohort=id.startsWith('positive_garage-')?'positive_garage':'main';return {group_id:id,n:row[0],mean_ratio:row[1],condition_list:conditions(row[2],cohort),cohort};}
    return S.cache.get(id);
  }
  function cacheRow(row) { S.cache.delete(row.group_id);S.cache.set(row.group_id,{...row,condition_list:row.condition_list||row.conditions?.split(' AND ')||[]});while(S.cache.size>1500)S.cache.delete(S.cache.keys().next().value); }
  function ref(id,text=id) { return `<button type="button" class="group-ref" data-group-id="${e(id)}">${e(text)}</button>`; }
  function hover(id) { const r=summary(id);return r?`${e(id)}<br>n=${num(r.n)} · ${pct(r.mean_ratio)}<br>${r.condition_list.map(e).join('<br>')}`:e(id); }
  const stat = (title,value,note) => `<div class="stat-card"><span class="stat-label">${title}</span><strong>${value}</strong><p>${note}</p></div>`;
  const note = (text,warm=false) => `<div class="evidence-note${warm?' warm':''}">${text}</div>`;
  const options = (values,selected) => values.map(v=>{const [value,text]=Array.isArray(v)?v:[v,v];return `<option value="${e(value)}"${String(value)===String(selected)?' selected':''}>${e(text)}</option>`;}).join('');
  const control = (id,title,values,value,wide=false) => `<label${wide?' class="wide"':''}>${title}<select id="${id}">${options(values,value)}</select></label>`;
  function heading(index,title,english,description,fixed=false) {return `<div class="view-heading"><div><span class="section-index">${index} / RESEARCH WORKBENCH</span><h2>${title}<span class="subheading">${english}</span></h2><p>${description}</p></div><span class="scope-pill">${fixed?'固定 2017 样本 · n = 8,595':e(meta().label)+' · n = '+num(meta().transactions)}</span></div>`;}
  function chart(id,title,english,caption,classes='') {
    const sources=(S.data.chart_sources[id]||[]).map(p=>p.replace('{cohort}',S.cohort));
    return `<section class="research-panel"><h3>${title}<small>${english}</small></h3><p class="caption">${caption}</p><div id="${id}" class="research-chart ${classes}"></div><div class="chart-tools"><button class="secondary" data-export="${id}">图表数据 CSV</button><button class="secondary" data-image="${id}">图表 SVG</button></div><p class="source-caption">Source: ${sources.map(e).join(' · ')}</p></section>`;
  }
  function plot(id,data,layout={},rows=[]) {
    S.exports.set(id,rows);
    const node=$(id);if(!node)return Promise.resolve();
    const base={paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'Microsoft YaHei,Segoe UI,sans-serif',size:12,color:'#526b80'},margin:{l:72,r:28,t:25,b:80},hoverlabel:{font:{size:12}},legend:{orientation:'h',x:0,y:-.23},xaxis:{gridcolor:'#edf1f5',zeroline:false},yaxis:{gridcolor:'#edf1f5',zeroline:false},...layout};
    return Plotly.react(node,data,base,{responsive:true,displaylogo:false,modeBarButtonsToRemove:['select2d','lasso2d']}).catch(err=>{if(node.isConnected)node.innerHTML='<p class="view-error">'+e(err.message)+'</p>';});
  }
  function horizontal(value,color=gray,dash='dash') {return {type:'line',xref:'paper',x0:0,x1:1,y0:value,y1:value,line:{color,width:1.2,dash}};}
  function groupTable(ids) {return `<div class="research-table"><table><thead><tr><th>组号 / Group</th><th>n</th><th>成交／估值</th><th>代表条件 / Representative conditions</th></tr></thead><tbody>${ids.map(id=>{const r=summary(id);return `<tr><td class="research-id-cell">${ref(id)}</td><td class="number">${num(r.n)}</td><td class="number">${pct(r.mean_ratio)}</td><td class="conditions-cell">${r.condition_list.map(e).join('<br>＋ ')}</td></tr>`;}).join('')}</tbody></table></div>`;}
  function clickPlot(id,callback) {$(id)?.removeAllListeners?.('plotly_click');$(id)?.on?.('plotly_click',ev=>callback(ev.points[0]));}
  function overview() {
    const n=meta().transactions, baseline=info().summary.overall_ratio;
    const t=S.data.thresholds.filter(r=>r.cohort===S.cohort&&r.min_n===100&&r.basis==='global_scaled');
    const relative=t.reduce((a,r)=>a+r.biased_groups,0);
    $('researchHost').innerHTML=heading('01','先看差距，再解释差距','Understand the gaps, then investigate their sources','分析单位始终是条件组。先找到组均成交／估值最高和最低的情况，再检查样本量、可比性、组合交互和表达复杂度。')+
      `<div class="stat-grid">${stat('原始组基准 / Cohort mean',pct(baseline),'高于 100%：成交价平均高于原估值。')}${stat('不同成员组 / Distinct groups',num(meta().groups),`${num(n)} 笔成交；相同成员的等价条件写法共用编号。`)}${stat('统一校准后仍偏离 ±5%',num(relative),'n ≥ 100；重叠组数量，不能理解成独立异常房屋。')}${stat('观测完整状态 / Profiles',num(info().summary.profiles),`${meta().fields.length} 个变量；三阶在这些观测状态上达到满秩。`)}</div>`+
      note('<strong>指标 / Metric</strong>　r<sub>G</sub> = mean<sub>i∈G</sub>(成交价<sub>i</sub> / 原估值<sub>i</sub>)。100% 是相等；110% 表示这组每笔比率的平均值为 1.10。先前的价格档位探索图使用交易中位数，已单独标明。')+
      `<div class="jump-grid">${[
        ['extremes','最高、最低的到底是什么组？','完整直方图、样本量边界和边缘组；组号直接关联条件。'],
        ['controls','放宽一个条件，差距如何变化？','原组、父组与新增成员；对照共同样本与标准化结果。'],
        ['interactions','为什么 a + b 不等于联合影响？','浏览 4,802 个四格比较，直接查看非加性差额。'],
        ['algebra','能用多简单的矩阵描述？','切换阶数、误差容限和真实完整状态核矩阵。'],
        ['validation','更复杂的模型预测更好吗？','空间与时间验证、误差改进和内部描述区间。'],
        ['coverage','结论覆盖哪些房屋？','信息覆盖率、价格选择偏差和估值分母兼容性。']
      ].map(([id,title,text])=>`<button class="jump-card" data-view="${id}">${title}<span>${text}</span></button>`).join('')}</div>`+
      `<div class="research-grid">${chart('priceChart','最初的问题：不同价格段的估值差距','Original exploration · transaction medians','2017 年 8,595 笔交易；中位数与 25–75% 分位区间。横轴是非等宽价格档位，不是线性价格轴。')}`+
      `<section class="research-panel"><h3>已经得到什么，以及尚未证明什么<small>Findings and their limits</small></h3>${note(`<strong>总体偏移与组间差异同时存在。</strong> 当前样本整体为 ${pct(baseline)}，应分别看原始比率和相对样本基准的差距。`)}${note('<strong>条件组合能显示单变量看不到的模式。</strong> 四格比较和共同样本标准化提供研究线索；组重叠、空间分布与选择过程仍会影响解释。')}${note('<strong>表达能力与预测能力需要分开检验。</strong> 三阶对已有完整状态达到数值精确，不代表未来房屋一定能被三阶模型准确预测。')}<p class="caption">所有视图复用已完成的分析。悬停编号可看条件，点击打开完整详情；每张图可导出数据和 SVG。</p></section></div>`;
    const rows=S.data.price_bands;
    $('researchHost').appendChild($('researchHost').querySelector('.jump-grid'));
    plot('priceChart',[{type:'scatter',mode:'lines+markers',x:rows.map(r=>r.price_band_label.split(' / ')[1]),y:rows.map(r=>100*r.median_ratio),line:{color:blue,width:2},marker:{size:7},error_y:{type:'data',symmetric:false,array:rows.map(r=>100*(r.q75-r.median_ratio)),arrayminus:rows.map(r=>100*(r.median_ratio-r.q25)),color:'#9bb8cd',thickness:2,width:6},customdata:rows.map(r=>[r.n,100*r.q25,100*r.q75]),hovertemplate:'%{x}<br>交易中位数 %{y:.2f}%<br>n=%{customdata[0]:,}<br>IQR %{customdata[1]:.2f}–%{customdata[2]:.2f}%<extra></extra>'}],{showlegend:false,shapes:[horizontal(100)],yaxis:{title:{text:'交易比率中位数 / Median (%)'},ticksuffix:'%',gridcolor:'#edf1f5'},xaxis:{title:{text:'成交价格档位 / Sale-price bands'},type:'category',tickangle:-22}},rows);
  }
  function extremes() {
    $('researchHost').innerHTML=heading('02','哪些组的成交／估值最高、最低？','Group extremes, support and exhaustive distributions','排序对象是组均值。样本量边界回答“在至少 n 笔成交的组里，差距还能有多大”；边缘组保留单变量与全部变量减一的原始筛选。')+
      `<section class="research-panel"><div class="research-controls">${control('tailN','最少成交数 / Minimum n',[1,10,30,100,300,500,1000,2000],S.minimum)}<button class="secondary" id="allRanks">进入完整组目录 / Browse all</button></div><div id="tailSummary"></div><div class="research-grid"><div><h3>最低 10 组 / Lowest</h3><div id="lowRanks"></div></div><div><h3>最高 10 组 / Highest</h3><div id="highRanks"></div></div></div><p class="caption">从全部不同成员组的既有完整排序中取前 10 个；同值组按原目录的稳定次序展示。可在目录继续查看全部结果。组均值的高低不等于因果影响大小。</p></section>`+
      `<div class="research-grid">${chart('frontierChart','样本量与极端均值','Exact support frontier','每个 n 都扫描全部合并组；虚线为当前样本整体均值。横轴为对数。')}`+
      `<section class="research-panel"><h3>原始差距与统一校准后的差距<small>Original versus globally calibrated gaps</small></h3><div class="research-controls">${control('biasBasis','比较基准 / Basis',[['original','原估值 · original'],['global_scaled','统一校准 · ratio / cohort mean'],['cohort_pp','相对基准 · ratio − cohort mean']],'global_scaled')}</div><div id="biasChart" class="research-chart"></div><div id="biasText"></div><div class="chart-tools"><button data-export="biasChart" class="secondary">图表数据 CSV</button></div><p class="source-caption">Source: group_bias/threshold_counts.csv</p></section></div>`+
      `<div class="research-grid"><section class="research-panel"><h3>任意大小的全部条件组写法<small>All supported expressions, by order</small></h3><div class="research-controls">${control('expressionOrder','条件数量 k / Order',[['all','所有 k = 1…'+meta().fields.length],...meta().fields.map((_,i)=>[i+1,'k = '+(i+1)])],'all')}</div><div id="expressionChart" class="research-chart"></div><div id="expressionSummary"></div><div class="chart-tools"><button data-export="expressionChart" class="secondary">图表数据 CSV</button><button data-image="expressionChart" class="secondary">图表 SVG</button></div><p class="source-caption">Source: edge_groups/${S.cohort}_histogram_by_k.csv</p></section>`+
      `<section class="research-panel"><h3>边缘组：1 个变量与 d−1 个变量<small>One-field and all-but-one-field extremes</small></h3><div class="research-controls">${control('edgeOrder','边缘阶数 / Edge order',[[1,'k = 1'],[meta().fields.length-1,'k = d − 1']],1)}${control('edgeSide','极值方向 / Tail',[['both','两端 / Both'],['low','最低 / Low'],['high','最高 / High']],'both')}</div><div id="edgeSummary"></div><div id="edgeTable"></div></section></div>`;
    $('tailN').onchange=()=>{S.minimum=Number($('tailN').value);drawTails();};
    $('allRanks').onclick=async()=>{show('directory');await window.GroupDirectory.browse(S.cohort,S.minimum,'high');};
    $('biasBasis').onchange=drawBias;$('expressionOrder').onchange=drawExpressions;$('edgeOrder').onchange=drawEdges;$('edgeSide').onchange=drawEdges;
    drawTails();drawBias();drawExpressions();drawEdges();
  }
  function drawTails() {
    const rows=info().frontier, current=rows.find(r=>r.min_n===S.minimum), ranks=info().rankings[S.minimum];
    $('tailSummary').innerHTML=note(`<strong>n ≥ ${num(S.minimum)}</strong>：${num(current?.distinct_groups||0)} 个不同成员组；最低 ${pct(current?.low_ratio)}，最高 ${pct(current?.high_ratio)}。悬停以下编号即可看组内条件。`);
    $('lowRanks').innerHTML=groupTable(ranks.low);$('highRanks').innerHTML=groupTable(ranks.high);
    plot('frontierChart',[
      {x:rows.map(r=>r.min_n),y:rows.map(r=>100*r.low_ratio),name:'最低 / Low',mode:'lines',line:{color:blue,width:2},hovertemplate:'n ≥ %{x}<br>最低 %{y:.2f}%<extra></extra>'},
      {x:rows.map(r=>r.min_n),y:rows.map(r=>100*r.high_ratio),name:'最高 / High',mode:'lines',fill:'tonexty',fillcolor:'#edf3f8',line:{color:orange,width:2},hovertemplate:'n ≥ %{x}<br>最高 %{y:.2f}%<extra></extra>'}
    ],{xaxis:{type:'log',title:{text:'最少成交数 / Minimum n'}},yaxis:{title:{text:'组均成交／估值 (%)'},ticksuffix:'%',gridcolor:'#edf1f5'},shapes:[horizontal(100*info().summary.overall_ratio),{type:'line',x0:S.minimum,x1:S.minimum,yref:'paper',y0:0,y1:1,line:{color:gray,dash:'dot',width:1}}]},rows);
  }
  function drawBias() {
    const basis=$('biasBasis').value, rows=S.data.thresholds.filter(r=>r.cohort===S.cohort&&r.basis===basis), levels=[...new Set(rows.map(r=>r.min_n))];
    plot('biasChart',['low','high'].map((side,i)=>{const r=rows.filter(r=>r.side===side);return {type:'bar',name:i?'高于阈值 / High':'低于阈值 / Low',x:r.map(x=>String(x.min_n)),y:r.map(x=>100*x.group_share),customdata:r.map(x=>[x.biased_groups,x.eligible_groups]),marker:{color:i?orange:blue},hovertemplate:'n ≥ %{x}<br>%{y:.3f}% 的组<br>%{customdata[0]:,} / %{customdata[1]:,}<extra>%{fullData.name}</extra>'};}),{barmode:'stack',xaxis:{type:'category',title:{text:'最少成交数 / Minimum n'},categoryarray:levels.map(String)},yaxis:{title:{text:'满足偏离阈值的组 / Share (%)'},ticksuffix:'%',range:[0,100],gridcolor:'#edf1f5'}},rows);
    $('biasText').innerHTML=note(basis==='global_scaled'?'每个组的均比率先除以样本整体均比率，再筛选低于 95% 或高于 105% 的组。分母是每个 n 门槛下全部不同成员组。':basis==='cohort_pp'?'筛选低于样本均值 5 个百分点或高于 5 个百分点的组；这与除以样本均值后的相对 5% 是不同口径。':'筛选原始均比率低于 95% 或高于 105% 的组；这包含样本整体的估值偏移。');
  }
  function drawExpressions() {
    const order=$('expressionOrder').value;
    const rows=order==='all'?info().histogram:info().histogram_orders.filter(r=>r.fields===Number(order)).map(r=>({...r,lower_pct:70+2*r.bin_index,upper_pct:72+2*r.bin_index}));
    const total=rows.reduce((s,r)=>s+r.group_count,0), singles=rows.reduce((s,r)=>s+r.singleton_group_count,0);
    plot('expressionChart',[
      {type:'bar',name:'组内 ≥ 2 笔 / n ≥ 2',x:rows.map(r=>r.lower_pct+1),y:rows.map(r=>r.group_count-r.singleton_group_count),marker:{color:blue},width:1.85,customdata:rows.map(r=>[r.lower_pct,r.upper_pct]),hovertemplate:'[%{customdata[0]}%, %{customdata[1]}%)<br>%{y:,} 条写法<extra>n ≥ 2</extra>'},
      {type:'bar',name:'组内 1 笔 / n = 1',x:rows.map(r=>r.lower_pct+1),y:rows.map(r=>r.singleton_group_count),marker:{color:'#c6d2dd'},width:1.85,customdata:rows.map(r=>[r.lower_pct,r.upper_pct]),hovertemplate:'[%{customdata[0]}%, %{customdata[1]}%)<br>%{y:,} 条写法<extra>n = 1</extra>'}
    ],{barmode:'stack',xaxis:{title:{text:'组均成交／估值 (%)'},ticksuffix:'%'},yaxis:{title:{text:'区间内条件写法数 / Expressions'},gridcolor:'#edf1f5'}},rows);
    $('expressionSummary').innerHTML=note(`共 <strong>${num(total)}</strong> 条有成员的条件写法；其中 ${pct(singles/total)} 只含 1 笔成交。这里保留全部条件写法，同一成员组可能被计数多次。<strong>不等于独立房屋数，也不等于合并组目录的组数。</strong>`);
  }
  function drawEdges() {
    const k=Number($('edgeOrder').value),side=$('edgeSide').value,rows=S.data.edges.filter(r=>r.cohort===S.cohort&&r.k===k&&(side==='both'||r.side===side));
    const overview=S.data.edge_summary.edges.find(r=>r.cohort===S.cohort&&r.k===k);
    $('edgeSummary').innerHTML=note(`在 ${num(overview.group_count)} 条边缘条件写法中，最低 ${pct(overview.min_ratio)}（${overview.low_ties} 条并列），最高 ${pct(overview.max_ratio)}（${overview.high_ties} 条并列）。下表保留并列；同一编号重复意味着写法不同、成员相同。`+(k>1?' 高阶极端组在这里均只有 1 笔成交，不能据此判断稳定的总体规律。':''));
    $('edgeTable').innerHTML=`<div class="research-table"><table><thead><tr><th>组号 / Canonical group</th><th>n · 比率</th><th>方向 / 写法</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${ref(r.group_id)}</td><td class="number">${r.n} · ${pct(r.mean_ratio)}</td><td>${r.side==='high'?'最高 / High':'最低 / Low'}<br>${e(r.conditions)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function controls() {
    const candidates=[...info().candidates].sort((a,b)=>a.label.localeCompare(b.label));
    if(!candidates.some(r=>r.group_id===S.comparison))S.comparison=candidates.find(r=>r.label.endsWith('025')).group_id;
    $('researchHost').innerHTML=heading('03','放宽一个条件后，谁进入了这个组？','Condition relaxation and common-support comparisons','选择已有候选组，再去掉一个条件。比较原组与新增成员的均值；控制变量后，先检查双方还有多少可比样本，再看差距是否保留。')+
      `<section class="research-panel"><div class="research-controls">${control('candidateSelect','候选组 / Candidate',candidates.map(r=>[r.group_id,`${r.label} · n=${r.n} · ${pct(r.mean_ratio)}`]),S.comparison,true)}${control('removedSelect','去掉的条件 / Removed condition',[],null,true)}${control('controlScheme','控制方案 / Controls',[['quarter','季度 / Quarter'],['location','季度＋位置 / + Location'],['property','季度＋房屋 / + Property'],['joint','季度＋位置＋房屋 / Joint']],'joint')}</div><div id="comparisonIntro"></div><div id="comparisonMeans" class="stat-grid"></div><div id="supportNote"></div></section>`+
      `<div class="research-grid">${chart('comparisonChart','从原始差距到标准化差距','Raw → common support → standardized','纵轴：原组均比率减去新增成员均比率，单位为百分点。空值表示缺少共同支持。')}`+
      `<section class="research-panel"><h3>所有控制方案并列查看<small>All four control specifications</small></h3><div id="controlTable"></div>${note('控制分析只对有共同分层单元的交易重新加权。样本变化和组成变化分别计量；剩余差距仍是条件关联，不能直接解释为被去掉变量的因果影响。')}<p id="controlCoverage" class="caption"></p></section></div>`+
      `<section class="research-panel"><div class="research-controls">${control('sliceMode','同一组的不同切片 / Slices',[['time','前后期 / Early–late'],['month','逐月 / Monthly'],['space','空间折 / Spatial folds']],'time')}</div><h3>这个组的偏差能否跨时间、空间出现？<small>Stability across observed slices</small></h3><div id="timeChart" class="research-chart"></div><div class="chart-tools"><button class="secondary" data-export="timeChart">图表数据 CSV</button></div><p class="source-caption">Source: group_atlas/${S.cohort}_slices.csv · 固定候选组的描述切片，不是新的独立确认。</p></section>`;
    function removedOptions(){const r=info().relaxations.filter(r=>r.group_id===S.comparison);const selected=r.some(r=>r.removed_field==='burglary')?'burglary':r[0].removed_field;$('removedSelect').innerHTML=options(r.map(r=>[r.removed_field,r.removed_condition]),selected);}
    removedOptions();
    $('candidateSelect').onchange=()=>{S.comparison=$('candidateSelect').value;removedOptions();drawComparison();drawSlices();};
    $('removedSelect').onchange=drawComparison;$('controlScheme').onchange=drawComparison;$('sliceMode').onchange=drawSlices;
    drawComparison();drawSlices();
  }
  function drawComparison() {
    const all=S.data.controls.filter(r=>r.cohort===S.cohort&&r.group_id===S.comparison&&r.removed_field===$('removedSelect').value),r=all.find(r=>r.scheme===$('controlScheme').value);
    const parent=summary(r.parent_id),computed=r.status==='computed';
    $('comparisonIntro').innerHTML=note(`原组 ${ref(r.group_id,r.label+' · '+r.group_id)}　→　去掉 <strong>${e(r.removed_condition)}</strong>　→　父组 ${ref(r.parent_id)}。新增成员 = 父组中的其余交易；比较的是原组与新增成员，两者不重叠。`);
    $('comparisonMeans').innerHTML=stat('原组 / Original',pct(r.original_ratio),'n = '+num(r.original_n))+stat('新增成员 / Added',pct(r.added_ratio),'n = '+num(r.added_n))+stat('父组 / Relaxed parent',pct(parent.mean_ratio),'n = '+num(parent.n))+stat('原组 − 新增 / Raw contrast',pp(r.raw_gap_pp),'算术均比率之差 / Difference in means');
    $('supportNote').innerHTML=computed?note(`<strong>当前控制保留：</strong>原组 ${r.common_original_n}/${r.original_n}（${pct(r.original_retention)}），新增 ${r.common_added_n}/${r.added_n}（${pct(r.added_retention)}）；${r.common_cells} 个共同分层单元。标准化均值为 ${pct(r.standardized_original_ratio)} 与 ${pct(r.standardized_added_ratio)}。<br>控制字段：${e(r.control_fields)}`):note('<strong>当前方案没有共同支持 / No common support。</strong> 原始比较仍可描述；控制后结果不可计算，不能把空值当作零差距。',true);
    const rows=[{stage:'原始 / Raw',gap_pp:r.raw_gap_pp},{stage:'共同样本 / Common support',gap_pp:r.common_gap_pp},{stage:'标准化 / Standardized',gap_pp:r.standardized_gap_pp}];
    plot('comparisonChart',[{type:'scatter',mode:'lines+markers+text',x:rows.map(x=>x.stage),y:rows.map(x=>x.gap_pp),text:rows.map(x=>x.gap_pp==null?'':pp(x.gap_pp)),textposition:'top center',line:{color:blue,width:2},marker:{size:10},connectgaps:false,hovertemplate:'%{x}<br>差距 %{y:.3f} pp<extra></extra>'}],{showlegend:false,shapes:[horizontal(0)],yaxis:{title:{text:'原组 − 新增 / Gap (pp)'},gridcolor:'#edf1f5'},xaxis:{type:'category'}},rows.map(x=>({...r,...x})));
    const names={quarter:'季度',location:'季度＋位置',property:'季度＋房屋',joint:'联合控制'};
    $('controlTable').innerHTML=`<div class="research-table"><table><thead><tr><th>控制 / Controls</th><th>保留原组 / 新增</th><th>标准化差距</th></tr></thead><tbody>${all.map(v=>`<tr><td>${names[v.scheme]}<span class="mini-note">${e(v.control_fields)}</span></td><td>${v.common_original_n} / ${v.common_added_n}</td><td>${v.status==='computed'?pp(v.standardized_gap_pp):'无共同支持 / Unavailable'}</td></tr>`).join('')}</tbody></table></div>`;
    const c=S.data.controls.filter(r=>r.cohort===S.cohort);$('controlCoverage').textContent=`当前样本的 ${num(c.length)} 个已有控制对照中，${num(c.filter(r=>r.status==='computed').length)} 个可计算。其余均保留“无共同支持”状态。`;
  }
  function drawSlices() {
    const kind=$('sliceMode').value,rows=info().slices.filter(r=>r.group_id===S.comparison&&(kind==='month'?r.period.startsWith('month-'):kind==='space'?r.period.startsWith('spatial-'):['Jan–Aug','Sep–Dec','amount-compatible'].includes(r.period)));
    plot('timeChart',[
      {name:'选定组 / Selected group',mode:'lines+markers',x:rows.map(r=>r.period),y:rows.map(r=>r.n?100*r.mean_ratio:null),customdata:rows.map(r=>[r.n,hover(r.group_id)]),line:{color:blue,width:2},marker:{size:8},connectgaps:false,hovertemplate:'%{x}<br>切片均比率 %{y:.2f}% · 切片 n=%{customdata[0]}<br>完整组：%{customdata[1]}<extra></extra>'},
      {name:'同切片样本 / Slice baseline',mode:'lines',x:rows.map(r=>r.period),y:rows.map(r=>100*r.cohort_period_mean),line:{color:gray,dash:'dash'},hovertemplate:'%{x}<br>样本均比率 %{y:.2f}%<extra></extra>'}
    ],{xaxis:{type:'category'},yaxis:{title:{text:'均比率 / Mean ratio (%)'},ticksuffix:'%',gridcolor:'#edf1f5'},shapes:[horizontal(100)]},rows);
  }
  function interactions() {
    const leads=S.data.leads.filter(r=>r.cohort_id===S.cohort);
    if(!S.data.interactions.some(r=>r.cohort===S.cohort&&r.interaction_id===S.interaction))S.interaction=leads[0]?.interaction_id;
    $('researchHost').innerHTML=heading('04','单独的影响，加起来等于联合影响吗？','Explore non-additive four-cell contrasts','每个比较包含两个变量的两个档位，共四个条件组。非加性差额 Δ = r₁₁ − r₁₀ − r₀₁ + r₀₀；它衡量描述性的交互，不是独立识别的因果效应。')+
      `<section class="research-panel"><div class="research-controls">${control('interactionField','包含变量 / Contains field',[['all','任意变量 / Any'],...meta().fields.map(f=>[f.name,f.label])],'all',true)}${control('interactionN','四格各至少 n / Minimum per cell',[1,10,30,50,100,200],30)}${control('interactionReference','参考资格 / Reference eligibility',[['eligible','符合既有参考条件 / Eligible'],['all','保留全部比较 / All']],'eligible')}${control('interactionSort','排序 / Order',[['absolute','|调整后 Δ| / Absolute'],['low','调整后 Δ 最低 / Lowest'],['high','调整后 Δ 最高 / Highest']],'absolute')}</div><div class="action-row">${leads.map(r=>`<button class="secondary" data-lead="${e(r.interaction_id)}">研究线索 ${e(r.label)}</button>`).join('')}</div><p id="interactionCount" class="caption"></p><div id="interactionScanChart" class="research-chart"></div><div class="chart-tools"><button class="secondary" data-export="interactionScanChart">筛选结果 CSV</button></div><div id="interactionTable"></div><p class="source-caption">Source: conditional/interactions.csv · 每个点是一个四格比较；不是一个房屋，也不是一个单独组。</p></section>`+
      `<div id="selectedInteraction"></div>`;
    for(const id of ['interactionField','interactionN','interactionReference','interactionSort'])$(id).onchange=()=>drawInteractionScan(true);
    $('interactionTable').onclick=ev=>{const row=ev.target.closest('[data-interaction]');if(row){S.interaction=row.dataset.interaction;drawSelectedInteraction();}};
    $('researchHost').querySelectorAll('[data-lead]').forEach(b=>b.onclick=()=>{S.interaction=b.dataset.lead;$('interactionField').value='all';$('interactionN').value='1';$('interactionReference').value='all';drawInteractionScan(false);$('selectedInteraction').scrollIntoView({block:'start'});});
    drawInteractionScan(false);
  }
  function drawInteractionScan(reset) {
    const field=$('interactionField').value,minimum=Number($('interactionN').value),eligible=$('interactionReference').value==='eligible',order=$('interactionSort').value;
    const rows=S.data.interactions.filter(r=>r.cohort===S.cohort&&(field==='all'||r.field_a===field||r.field_b===field)&&Math.min(r.n00,r.n01,r.n10,r.n11)>=minimum&&(!eligible||r.eligible_reference));
    rows.sort((a,b)=>order==='absolute'?Math.abs(b.adjusted_interaction)-Math.abs(a.adjusted_interaction):order==='high'?b.adjusted_interaction-a.adjusted_interaction:a.adjusted_interaction-b.adjusted_interaction);
    if(reset||!rows.some(r=>r.interaction_id===S.interaction))S.interaction=rows[0]?.interaction_id;
    $('interactionCount').textContent=`当前筛选 ${num(rows.length)} 个四格比较；图中显示全部，表中列出排序前 ${Math.min(100,rows.length)} 个。既有扫描本身有纳入条件，不代表所有理论交互。`;
    const tbody=rows.slice(0,100).map(r=>`<tr data-interaction="${e(r.interaction_id)}" tabindex="0"><td>${e(label(r.field_a))}<br>× ${e(label(r.field_b))}</td><td>${Math.min(r.n00,r.n01,r.n10,r.n11)}</td><td class="number">${pp(100*r.raw_interaction)}</td><td class="number">${pp(100*r.adjusted_interaction)}</td><td>${r.eligible_reference?'参考可用 / Eligible':'仅描述 / Descriptive'}</td></tr>`).join('');
    $('interactionTable').innerHTML=`<div class="research-table"><table><thead><tr><th>变量对 / Variables · 点击查看四格</th><th>最小格 n</th><th>原始 Δ</th><th>调整后 Δ</th><th>参考状态</th></tr></thead><tbody>${tbody||'<tr><td colspan="5">无符合条件的比较 / No matching comparisons</td></tr>'}</tbody></table></div>`;
    $('interactionTable').onkeydown=ev=>{if(ev.key==='Enter'){const row=ev.target.closest('[data-interaction]');if(row){S.interaction=row.dataset.interaction;drawSelectedInteraction();}}};
    plot('interactionScanChart',[{type:'scatter',mode:'markers',x:rows.map(r=>100*r.raw_interaction),y:rows.map(r=>100*r.adjusted_interaction),customdata:rows.map(r=>[r.interaction_id,label(r.field_a)+' × '+label(r.field_b),Math.min(r.n00,r.n01,r.n10,r.n11)]),marker:{color:blue,size:6,opacity:.6},hovertemplate:'%{customdata[1]}<br>原始 Δ %{x:.2f} pp<br>调整后 Δ %{y:.2f} pp<br>四格最小 n=%{customdata[2]}<br>点击查看四个具体组<extra></extra>'}],{showlegend:false,xaxis:{title:{text:'原始 Δ / Raw (pp)'},zeroline:true,zerolinecolor:'#bbc7d2'},yaxis:{title:{text:'调整后 Δ / Adjusted (pp)'},zeroline:true,zerolinecolor:'#bbc7d2',gridcolor:'#edf1f5'}},rows).then(()=>clickPlot('interactionScanChart',point=>{S.interaction=point.customdata[0];drawSelectedInteraction();$('selectedInteraction').scrollIntoView({block:'start'});}));
    drawSelectedInteraction();
  }
  function drawSelectedInteraction() {
    const r=S.data.interactions.find(r=>r.cohort===S.cohort&&r.interaction_id===S.interaction);
    if(!r){$('selectedInteraction').innerHTML=note('没有可显示的比较。可降低四格样本门槛或放宽参考资格筛选。');return;}
    const lead=S.data.leads.find(l=>l.interaction_id===r.interaction_id&&l.cohort_id===S.cohort);
    const cells=['00','01','10','11'];
    $('selectedInteraction').innerHTML=`<div class="research-grid"><section class="research-panel"><h3>${e(label(r.field_a))} × ${e(label(r.field_b))}<small>Selected four-cell comparison${lead?' · '+e(lead.label):''}</small></h3><div class="research-controls">${control('interactionMetric','四格纵轴 / Cell metric',[['raw','原始组均比率 / Original mean'],['adjusted','加性调整后残差 / Adjusted residual']],'raw')}</div><div id="interactionChart" class="research-chart"></div><div class="chart-tools"><button class="secondary" data-export="interactionChart">四格数据 CSV</button><button class="secondary" data-image="interactionChart">图表 SVG</button></div><p class="source-caption">Source: conditional/interactions.csv · 11 格的虚线点为由另三格推出的加性值。</p></section><section class="research-panel"><h3>四个具体组<small>The four groups behind the contrast</small></h3><div class="cell-grid">${cells.map((cell,i)=>`<div class="cell-card"><span class="cell-label">${cell} · n = ${num(r['n'+cell])}</span><strong>${pct(r['mean'+cell])}</strong>${ref(r.cell_groups[i])}<p>${e(label(r.field_a))} = ${e(category(r.field_a,r['a'+cell[0]]))}<br>${e(label(r.field_b))} = ${e(category(r.field_b,r['b'+cell[1]]))}</p></div>`).join('')}</div>${note(`原始 Δ = <strong>${pp(100*r.raw_interaction)}</strong>；加性调整后 Δ = <strong>${pp(100*r.adjusted_interaction)}</strong>。<br>四格最少空间簇 ${r.min_cell_clusters}；${r.eligible_reference?'符合既有 maxT 内部参考条件，参考值 '+Number(r.maxT_reference_p).toFixed(4):'未满足参考资格，仅保留描述结果'}。`)}${lead?note(`既有线索 ${e(lead.label)}：四类比较调整后参考 ${lead.reference.toFixed(4)}；前期 ${pp(lead.early_pp)}；后期 ${pp(lead.late_pp)}；估值金额兼容子样本 ${pp(lead.compatible_pp)}。最小空间切片 n = ${lead.spatial_min_n}。`):''}<p class="caption">参考统计使用已固定的拟合/选择结果。它不是新数据上的确认性显著性检验；所选比较需结合空间支持与后续验证。</p></section></div>`;
    $('interactionMetric').onchange=()=>drawFourCells(r);drawFourCells(r);
    $('interactionTable')?.querySelectorAll('[data-interaction]').forEach(el=>el.classList.toggle('selected',el.dataset.interaction===S.interaction));
  }
  function drawFourCells(r) {
    const adjusted=$('interactionMetric').value==='adjusted',cells=['00','01','10','11'],values=cells.map(c=>100*r[(adjusted?'residual':'mean')+c]),prediction=values[2]+values[1]-values[0];
    const rows=cells.map((cell,i)=>({cell,interaction_id:r.interaction_id,metric:adjusted?'adjusted_residual':'original_mean_ratio',unit:adjusted?'percentage_points':'percent',additive_prediction:i===3?prediction:values[i],group_id:r.cell_groups[i],n:r['n'+cell],mean_ratio:r['mean'+cell],adjusted_residual_pp:100*r['residual'+cell],plotted_value:values[i],conditions:summary(r.cell_groups[i]).condition_list.join(' AND ')}));
    plot('interactionChart',[{type:'scatter',mode:'lines+markers',x:['A0 · B0','A0 · B1'],y:values.slice(0,2),name:'A0: '+category(r.field_a,r.a0),line:{color:blue,width:2},customdata:r.cell_groups.slice(0,2),text:r.cell_groups.slice(0,2).map(hover),hovertemplate:'%{text}<br>当前纵轴 %{y:.2f}<extra>A0</extra>'},{type:'scatter',mode:'lines+markers',x:['A0 · B0','A0 · B1'],y:values.slice(2,4),name:'A1: '+category(r.field_a,r.a1),line:{color:orange,width:2},customdata:r.cell_groups.slice(2,4),text:r.cell_groups.slice(2,4).map(hover),hovertemplate:'%{text}<br>当前纵轴 %{y:.2f}<extra>A1</extra>'},{type:'scatter',mode:'lines+markers',x:['A0 · B0','A0 · B1'],y:[values[2],prediction],name:'A1 加性预期 / Additive',line:{color:gray,dash:'dash'},marker:{symbol:'circle-open',size:9},hovertemplate:'加性预期 %{y:.2f}<extra>由另三格计算</extra>'}],{xaxis:{type:'category',tickvals:['A0 · B0','A0 · B1'],ticktext:['B0: '+category(r.field_b,r.b0),'B1: '+category(r.field_b,r.b1)],title:{text:label(r.field_b)}},yaxis:{title:{text:adjusted?'调整残差 / Residual (pp)':'组均比率 / Mean (%)'},gridcolor:'#edf1f5'},legend:{orientation:'h',x:0,y:-.35},margin:{l:65,r:24,t:20,b:100}},rows).then(()=>clickPlot('interactionChart',point=>{if(typeof point.customdata==='string')window.GroupDirectory.open(point.customdata);}));
  }
  function algebra() {
    const minimums=[...new Set(info().errors.map(r=>r.minimum_n))];
    $('researchHost').innerHTML=heading('05','数百万个组，归结为计数、和与选择矩阵','Sparse profiles, exact aggregation and interaction order','完整状态把所有变量的档位都固定下来。每个条件组只是这些状态的一个集合：保留状态的交易数 n 与比率之和 s，就能精确恢复任意有成员的组均值。')+
      `<section class="research-panel"><div class="equation">r<sub>G</sub> = (1ᵀ D<sub>G</sub> s) / (1ᵀ D<sub>G</sub> n)　<small>D<sub>G</sub> = ∏<sub>j∈G</sub> D<sub>j</sub></small></div><p class="caption">D 是对角选择矩阵；同时满足多个条件等于把选择矩阵相乘。s 记录各完整状态的比率总和，n 记录交易数；必须按交易数加权，不能直接平均完整状态均值。</p><div class="stat-grid">${stat('实际观测状态 / Observed profiles',num(info().summary.profiles),'所有变量同时固定的非空状态。')}${stat('理论稠密格数 / Dense cells',Number(info().summary.dense_cells).toExponential(3),'包含未观测的组合；不对这些空格外推。')}${stat('已精确归约的组 / Exact groups',num(meta().groups),'同成员写法合并；逐组计数已核验。')}${stat('原始变量数 / Fields',meta().fields.length,'高维选择保留在稀疏状态中。')}</div></section>`+
      `<section class="research-panel" style="margin-top:18px"><div class="research-controls"><label>交互阶数 k / Degree <output id="degreeLabel"></output><input type="range" id="algebraDegree" min="0" max="3" value="${S.degree}"></label>${control('algebraN','组内最少成交 / Minimum n',minimums,100)}${control('algebraTolerance','允许的最大重构误差 / Tolerance (pp)',[[.1,'0.1 pp'],[.5,'0.5 pp'],[1,'1 pp'],[2,'2 pp']],1)}</div><div id="algebraSummary"></div></section>`+
      `<div class="research-grid">${chart('rankChart','随阶数增加，能表达多少独立状态？','Numerical rank on observed support','灰色虚线是观测完整状态数量；秩越高，已有状态上的表达能力越强。')}${chart('errorChart','全部组的最大重构误差','Maximum reconstruction error over all eligible groups','误差针对已有组均值，单位为百分点。颜色使用对数刻度；点击格子切换阶数与样本门槛。')}</div>`+
      `<section class="research-panel"><h3>查看真实状态的核矩阵<small>Actual profile kernel · a movable 24 × 24 window</small></h3><div class="equation">K<sub>k</sub>(h) = ∑<sub>t=0…k</sub> C(h,t) / ∑<sub>t=0…k</sub> C(d,t)</div><p class="caption">h 是两个完整状态中相同档位的变量数量，d 是变量总数。这是实际数据计算的矩阵窗口，不是示意图。改变 k 会改变矩阵；每个格子的行、列都对应可查询的完整状态组。</p><div class="research-controls"><label>起始状态序号 / First profile (0-based)<input id="profileStart" type="number" min="0" max="${Math.max(0,info().profiles.length-24)}" step="24" value="${S.profileStart}"></label><button id="previousProfiles" class="secondary">前 24 个</button><button id="nextProfiles" class="secondary">后 24 个</button><label class="check-label"><input type="checkbox" id="weightedKernel">显示 B = √n K √n / Count-weighted</label></div><div id="kernelChart" class="research-chart matrix"></div><div class="chart-tools"><button class="secondary" data-export="kernelChart">矩阵数据 CSV</button><button class="secondary" data-image="kernelChart">矩阵 SVG</button></div><div id="profileTable"></div><p class="source-caption">Source: group_algebra/${S.cohort}_profiles.csv · 点击格子查看列对应的完整状态。</p></section>`+
      note('<strong>三阶数值精确 ≠ 偏误机制只有三阶。</strong> 三阶在这批稀疏的观测状态上已满秩，仍需要与观测状态数量同阶的自由度。它描述已有状态均值；不保证未观测组合、同状态内单笔交易或未来房屋的预测准确。',true);
    $('algebraDegree').oninput=()=>{S.degree=Number($('algebraDegree').value);drawAlgebra();drawKernel();};
    $('algebraN').onchange=drawAlgebra;$('algebraTolerance').onchange=drawAlgebra;
    function move(value){S.profileStart=Math.min(Math.max(0,Math.trunc(Number(value)||0)),Math.max(0,info().profiles.length-24));$('profileStart').value=S.profileStart;drawKernel();}
    $('profileStart').onchange=()=>move($('profileStart').value);$('previousProfiles').onclick=()=>move(S.profileStart-24);$('nextProfiles').onclick=()=>move(S.profileStart+24);$('weightedKernel').onchange=drawKernel;
    drawAlgebra();drawKernel();
  }
  function drawAlgebra() {
    const minimum=Number($('algebraN').value),tol=Number($('algebraTolerance').value),row=info().errors.find(r=>r.degree===S.degree&&r.minimum_n===minimum),order=info().orders.find(r=>r.degree===S.degree);
    const needed=info().errors.filter(r=>r.minimum_n===minimum&&r.degree>=0&&r.max_abs_pp<=tol).sort((a,b)=>a.degree-b.degree)[0];
    const errorText=row.max_abs_pp<1e-8?row.max_abs_pp.toExponential(2):row.max_abs_pp.toFixed(3);
    $('degreeLabel').textContent='k = '+S.degree;
    $('algebraSummary').innerHTML=note(`<strong>当前 k = ${S.degree}</strong>：秩 ${num(order.rank)} / ${num(order.profiles)}。对全部 ${num(row.groups)} 个 n ≥ ${num(minimum)} 的组，最大重构误差为 <strong>${errorText} pp</strong>，RMSE ${row.rmse_pp<1e-8?row.rmse_pp.toExponential(2):row.rmse_pp.toFixed(3)} pp。<br>最坏误差对应 ${ref(row.worst_group_id)}；允许最大误差 ≤ ${tol} pp 时，已计算阶数中最低为 <strong>${needed?needed.degree:'未达到'}</strong>。`);
    plot('rankChart',[{type:'bar',x:info().orders.map(r=>String(r.degree)),y:info().orders.map(r=>r.rank),marker:{color:info().orders.map(r=>r.degree===S.degree?blue:'#bbccd9')},text:info().orders.map(r=>num(r.rank)),textposition:'outside',cliponaxis:false,customdata:info().orders.map(r=>100*r.explained_fraction),hovertemplate:'k=%{x}<br>秩 %{y:,}<br>状态方差解释 %{customdata:.2f}%<extra></extra>'}],{showlegend:false,xaxis:{type:'category',title:{text:'最高交互阶数 / Maximum degree'}},yaxis:{title:{text:'数值秩 / Numerical rank'},range:[0,info().summary.profiles*1.15],gridcolor:'#edf1f5'},shapes:[horizontal(info().summary.profiles)]},info().orders);
    const levels=[...new Set(info().errors.map(r=>r.minimum_n))],z=[],text=[],custom=[];
    for(let k=0;k<=3;k++){const rows=levels.map(n=>info().errors.find(r=>r.degree===k&&r.minimum_n===n));z.push(rows.map(r=>Math.log10(Math.max(1e-12,r.max_abs_pp))));text.push(rows.map(r=>r.max_abs_pp<1e-8?'≈ 0':r.max_abs_pp.toFixed(2)));custom.push(rows.map(r=>[r.degree,r.minimum_n,r.max_abs_pp,r.groups]));}
    plot('errorChart',[{type:'heatmap',x:levels.map(String),y:['k=0','k=1','k=2','k=3'],z,text,texttemplate:'%{text}',customdata:custom,colorscale:[[0,'#edf4f9'],[.7,'#b5cadd'],[1,'#265d8b']],zmin:-12,zmax:2,colorbar:{title:{text:'最大 pp'},tickvals:[-12,-6,-2,0,2],ticktext:['≤1e−12','1e−6','0.01','1','100'],thickness:12},hovertemplate:'k=%{customdata[0]} · n ≥ %{customdata[1]}<br>%{customdata[3]:,} 个组<br>最大误差 %{customdata[2]:.4g} pp<extra></extra>'}],{showlegend:false,xaxis:{type:'category',title:{text:'组内最少成交 / Minimum n'}},yaxis:{autorange:'reversed',title:{text:'最高阶数 / Degree'}},margin:{l:62,r:75,t:20,b:70}},info().errors.filter(r=>r.degree>=0)).then(()=>clickPlot('errorChart',point=>{S.degree=point.customdata[0];$('algebraDegree').value=S.degree;$('algebraN').value=point.customdata[1];drawAlgebra();drawKernel();}));
  }
  function choose(n,k) {if(k>n)return 0;let result=1;for(let i=1;i<=k;i++)result*=((n-i+1)/i);return result;}
  function drawKernel() {
    const profiles=info().profiles.slice(S.profileStart,S.profileStart+24),d=meta().fields.length,k=S.degree,weighted=$('weightedKernel').checked;
    let denominator=0;for(let t=0;t<=k;t++)denominator+=choose(d,t);
    const z=[],custom=[],rows=[];
    for(const a of profiles){const line=[],metaLine=[];for(const b of profiles){let h=0;for(let j=0;j<d;j++)if(a[3+j]===b[3+j])h++;let value=0;for(let t=0;t<=k;t++)value+=choose(h,t);value/=denominator;const plotted=weighted?value*Math.sqrt(a[1]*b[1]):value;line.push(plotted);metaLine.push([a[0],b[0],h,a[1],b[1],pct(a[2]),pct(b[2])]);rows.push({row_group:a[0],column_group:b[0],equal_fields:h,degree:k,kernel:value,count_weighted:weighted,value:plotted});}z.push(line);custom.push(metaLine);}
    const ticks=profiles.map((_,i)=>'P'+(S.profileStart+i));
    plot('kernelChart',[{type:'heatmap',x:ticks,y:ticks,z,customdata:custom,colorscale:[[0,'#f3f7fa'],[.5,'#89adca'],[1,'#235c8b']],zmin:0,zmax:weighted?Math.max(...profiles.map(r=>r[1])):1,colorbar:{title:{text:weighted?'B':'K'},thickness:13},hovertemplate:'行 %{customdata[0]} · n=%{customdata[3]} · %{customdata[5]}<br>列 %{customdata[1]} · n=%{customdata[4]} · %{customdata[6]}<br>相同档位数 h=%{customdata[2]}<br>矩阵值 %{z:.5f}<br>下表悬停编号看条件；点击打开列状态<extra></extra>'}],{showlegend:false,xaxis:{type:'category',tickangle:-55,title:{text:'列完整状态 / Column profile'}},yaxis:{autorange:'reversed',type:'category',title:{text:'行完整状态 / Row profile'}},margin:{l:62,r:55,t:15,b:78}},rows).then(()=>clickPlot('kernelChart',point=>window.GroupDirectory.open(point.customdata[1])));
    const prefix=S.cohort==='main'?'M':'G';
    $('profileTable').innerHTML=`<div class="research-table"><table><thead><tr><th>图中状态 / Profile</th><th>正式组号 / Canonical group</th><th>n</th><th>均比率</th><th>具体条件 / Conditions</th></tr></thead><tbody>${profiles.map((r,i)=>`<tr><td>${ref(r[0],prefix+'-P'+String(S.profileStart+i).padStart(6,'0'))}</td><td>${ref(r[0])}</td><td>${r[1]}</td><td>${pct(r[2])}</td><td class="conditions-cell">${summary(r[0]).condition_list.map(e).join('<br>')}</td></tr>`).join('')}</tbody></table></div>`;
    $('previousProfiles').disabled=S.profileStart===0;$('nextProfiles').disabled=S.profileStart>=info().profiles.length-24;
  }
  function validation() {
    $('researchHost').innerHTML=heading('06','表达更复杂，预测一定更好吗？','Prediction is a separate empirical question','这里比较已保存的空间验证和向前时间验证。横轴是相对于统一校准模型的 MSE 改进百分比；负数表示误差更大。')+
      `<section class="research-panel"><div class="research-controls">${control('validationScheme','验证方式 / Split',[['spatial','空间折外 / Spatial'],['forward','向前时间 / Forward']],'spatial')}${S.cohort==='main'?'<label class="check-label"><input id="compatibleOnly" type="checkbox">2017 金额兼容子样本 / Compatible sensitivity</label>':''}</div><div id="validationSummary"></div></section>`+
      `<div class="research-grid">${chart('performanceChart','相对统一校准的预测误差改进','Relative MSE gain against global calibration','点为改进比例；横线是内部固定预测的聚类 bootstrap 描述区间。0 表示没有改进。')}`+
      `<section class="research-panel"><h3>绝对误差与实际评价样本<small>Absolute errors and evaluation support</small></h3><div id="performanceTable"></div>${note('MSE 改进的单位是百分比；比率 RMSE 的单位是百分点，两者不能混用。空间与时间划分使用的评价交易也可能不同，应在同一划分内比较模型。')}${note('<strong>不是新的独立确认。</strong> 这些区间以既有预测与拟合结果为固定对象。挑出的交互、同数据上的复核和更复杂表达，并不自动构成样本外证据。',true)}</section></div>`+
      `<section class="research-panel"><h3>配对分析的证据强度也需要看平衡<small>Matching balance matters</small></h3><div id="matchingSummary"></div><p class="caption">Source: conditional/report_summary.json · 本段为两样本既有匹配研究的合计摘要，不能将未通过平衡的结果解释为单变量机制。</p></section>`;
    $('validationScheme').onchange=drawValidation;if($('compatibleOnly'))$('compatibleOnly').onchange=drawValidation;
    const c=S.data.conditional_summary;
    $('matchingSummary').innerHTML=note(`既有 ${c.comparison_total} 项匹配比较中，${c.comparisons_meeting_exploratory_balance} 项满足探索性平衡标准，${c.comparisons_without_matches} 项没有匹配。低保留率或匹配后仍不平衡的对照，证据强度不足以识别单独机制。`);
    drawValidation();
  }
  function drawValidation() {
    const cohort=$('compatibleOnly')?.checked?'main_2017_compatible':S.cohort,scheme=$('validationScheme').value;
    const rows=S.data.gains.filter(r=>r.cohort===cohort&&r.scheme===scheme),performance=S.data.performance.filter(r=>r.cohort===cohort&&r.scheme===scheme);
    const names={original:'原估值 / Original',global:'统一校准 / Global',additive:'加性 / Additive',interaction:'加性＋交互 / Interaction'};
    const additive=rows.find(r=>r.model==='additive');
    $('validationSummary').innerHTML=note(`<strong>${cohort==='main_2017_compatible'?'2017 金额兼容子样本':e(meta().label)} · ${scheme==='spatial'?'空间验证':'时间验证'}</strong>：评价 n = ${num(performance[0].n)}。加性模型的相对 MSE 改进 ${pct(additive.mse_gain)}；描述区间 ${pct(additive.cluster_bootstrap_low)} 至 ${pct(additive.cluster_bootstrap_high)}。`);
    plot('performanceChart',[{type:'scatter',mode:'markers',x:rows.map(r=>100*r.mse_gain),y:rows.map(r=>names[r.model]),marker:{size:11,color:blue},error_x:{type:'data',symmetric:false,array:rows.map(r=>100*(r.cluster_bootstrap_high-r.mse_gain)),arrayminus:rows.map(r=>100*(r.mse_gain-r.cluster_bootstrap_low)),color:'#8ca9c1',thickness:2,width:6},customdata:rows.map(r=>[100*r.cluster_bootstrap_low,100*r.cluster_bootstrap_high,r.clusters,r.draws]),hovertemplate:'%{y}<br>改进 %{x:.3f}%<br>区间 %{customdata[0]:.3f}–%{customdata[1]:.3f}%<br>%{customdata[2]} 簇 · %{customdata[3]} 次<extra></extra>'}],{showlegend:false,xaxis:{title:{text:'相对 MSE 改进 / Improvement (%)'},ticksuffix:'%',zeroline:true,zerolinecolor:gray},yaxis:{type:'category',autorange:'reversed'},margin:{l:158,r:35,t:32,b:74}},rows);
    $('performanceTable').innerHTML=`<div class="research-table"><table><thead><tr><th>模型 / Model</th><th>评价 n</th><th>比率 RMSE / pp</th><th>比率 MAE / pp</th></tr></thead><tbody>${performance.map(r=>`<tr><td>${names[r.model]}</td><td>${num(r.n)}</td><td>${(100*r.ratio_rmse).toFixed(3)}</td><td>${(100*r.ratio_mae).toFixed(3)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function coverage() {
    $('researchHost').innerHTML=heading('07','信息覆盖是否随价格变化？','Availability, historical scope and denominator sensitivity','这页使用固定的 2017 年 8,595 笔基础交易，不随上方研究样本选择而改变。每一格显示该价格档位的可用数／基础数；选择一行查看定义。',true)+
      `<section class="research-panel"><div class="research-controls">${control('coverageMode','显示 / Display',[['available','可用比例 / Available'],['missing','缺失比例 / Missing']],'available')}${control('coverageField','查看字段 / Field',S.data.availability.map(r=>[r.field,r.label_zh+' / '+r.label_en]),'garage',true)}</div><div id="coverageChart" class="research-chart tall"></div><div id="coverageDefinition"></div><div class="chart-tools"><button class="secondary" data-export="coverageChart">覆盖数据 CSV</button><button class="secondary" data-image="coverageChart">覆盖图 SVG</button></div><p class="source-caption">Source: selection_audit/coverage_by_price.csv · availability_summary.csv</p></section>`+
      `<div class="research-grid"><section class="research-panel"><h3>历史信息与尚缺的数据<small>Historical context and known gaps</small></h3>${note('犯罪变量采用成交前 365 天、500 米范围的事件计数；学校使用已保存的历史学年口径。可用与否、年份兼容与否是不同维度，不能用当前信息替代当年的状态。')}${note('学校档位来自所用报告的评级定义；不能自动改称所有地区通用的“A级学区”。车库变量是正容量样本中的档位，编码 0 不是“无车库”。')}${note('<strong>封闭社区 / Gated access：没有可用分类。</strong> 没有数据应显示未知，不能从缺失推断为开放社区。')}<p class="caption">外部信息沿用已收集数据。本次工作台整合不添加新的外部检索结果。</p></section><section class="research-panel"><h3>研究样本的分母与覆盖<small>Cohort and assessment-denominator scope</small></h3><div id="scopeTable"></div>${note('原估值分母保持不变。官方 2017 估值的诊断只比较同一批正分母记录；差异不意味着可以直接更换全样本分母。')}<div id="denominatorTable"></div></section></div>`+
      `<section class="research-panel"><h3>每个核心图都有可下载的来源<small>Traceable evidence</small></h3><p class="caption">CSV 导出包含当前图的实际数据；原始结果表 ZIP 保留下面的目录结构。SHA-256 对应构建时的输入文件。完整工作台快照还包含图与信源的对应表。</p><div class="action-row"><a href="research-sources.zip" class="button secondary">原始结果表 ZIP</a><a href="research-data.json" class="button secondary" download>完整数据快照</a></div><details><summary>查看 ${S.data.sources.length} 个来源 / View source manifest</summary><div class="research-table"><table><thead><tr><th>来源文件 / Source</th><th>行数</th><th>SHA-256</th></tr></thead><tbody>${S.data.sources.map(r=>`<tr><td>${e(r.path)}</td><td>${r.rows==null?'—':num(r.rows)}</td><td style="font-family:Consolas;overflow-wrap:anywhere">${e(r.sha256)}</td></tr>`).join('')}</tbody></table></div></details></section>`;
    const scopes=S.data.scope,names={main:'主样本 / Main',positive_garage:'正车库 / Garage',main_2017_compatible:'金额兼容 / Compatible'};
    $('scopeTable').innerHTML=`<div class="research-table"><table><thead><tr><th>样本</th><th>n / 基础数</th><th>覆盖率</th><th>均比率</th></tr></thead><tbody>${scopes.map(r=>`<tr><td>${names[r.cohort]}</td><td>${num(r.n)} / ${num(r.source_n)}</td><td>${pct(r.coverage)}</td><td>${pct(r.mean_ratio)}</td></tr>`).join('')}</tbody></table></div>`;
    $('denominatorTable').innerHTML=`<div class="research-table"><table><thead><tr><th>同记录诊断样本</th><th>n</th><th>原分母比率</th><th>官方 2017 分母比率</th></tr></thead><tbody>${scopes.filter(r=>r.cohort!=='main_2017_compatible').map(r=>`<tr><td>${names[r.cohort]}<span class="mini-note">排除 ${r.official_2017_zero_n} 个官方零分母</span></td><td>${r.denominator_diagnostic_n}</td><td>${pct(r.denominator_original_mean)}</td><td>${pct(r.denominator_official2017_mean)}</td></tr>`).join('')}</tbody></table></div>`;
    if(!$('coverageField').value)$('coverageField').selectedIndex=0;
    $('coverageMode').onchange=drawCoverage;$('coverageField').onchange=drawCoverageDefinition;drawCoverage();
  }
  function drawCoverage() {
    const missing=$('coverageMode').value==='missing',fields=S.data.availability,bands=[...new Map(S.data.coverage.map(r=>[r.price_band_index,r.price_band_label])).entries()].sort((a,b)=>a[0]-b[0]);
    const rows=fields.map(f=>bands.map(([i])=>S.data.coverage.find(r=>r.field===f.field&&r.price_band_index===i)));
    plot('coverageChart',[{type:'heatmap',x:bands.map(([,v])=>v.split(' / ').at(-1)),y:fields.map(r=>r.label_zh),z:rows.map(r=>r.map(x=>100*(missing?1-x.coverage:x.coverage))),text:rows.map(r=>r.map(x=>(100*(missing?1-x.coverage:x.coverage)).toFixed(0)+'%')),texttemplate:'%{text}',customdata:rows.map(r=>r.map(x=>[x.field,x.available_n,x.base_n,x.label_en])),colorscale:[[0,'#f3f6f9'],[.5,'#8db1cd'],[1,'#28658e']],zmin:0,zmax:100,colorbar:{ticksuffix:'%',thickness:12},hovertemplate:'%{y} / %{customdata[3]}<br>%{x}<br>可用 %{customdata[1]:,} / %{customdata[2]:,}<br>当前比例 %{z:.2f}%<extra></extra>'}],{showlegend:false,xaxis:{type:'category',tickangle:-25,title:{text:'成交价格档位 / Price band'}},yaxis:{type:'category',autorange:'reversed',automargin:true},margin:{l:156,r:45,t:15,b:83}},S.data.coverage.map(r=>({...r,display:missing?'missing':'available',plotted_percent:100*(missing?1-r.coverage:r.coverage)}))).then(()=>clickPlot('coverageChart',point=>{$('coverageField').value=point.customdata[0];drawCoverageDefinition();}));
    drawCoverageDefinition();
  }
  function drawCoverageDefinition() {
    const r=S.data.availability.find(r=>r.field===$('coverageField').value);if(!r)return;
    $('coverageDefinition').innerHTML=note(`<strong>${e(r.label_zh)} / ${e(r.label_en)}</strong>：总体可用 ${num(r.available_n)} / ${num(r.base_n)}（${pct(r.coverage)}）；各价格段覆盖率 ${pct(r.min_band_coverage)} 至 ${pct(r.max_band_coverage)}，相差 ${r.band_gap_pp.toFixed(2)} 个百分点。<br>${e(r.definition)}<br><strong>推断范围：</strong>${e(r.allowed_inference_scope)}；不得自动推广至未覆盖房屋。`);
  }
  function downloadCSV(id) {
    const rows=S.exports.get(id);if(!rows?.length)return;
    const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];
    function cell(v){if(v==null)return '';let s=typeof v==='object'?JSON.stringify(v):String(v);if(typeof v==='string'&&/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
    const text='\uFEFF'+[keys.map(cell).join(','),...rows.map(r=>keys.map(k=>cell(r[k])).join(','))].join('\r\n');
    const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=id+'-'+S.cohort+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  function writeHash() {
    const hash=new URLSearchParams(location.hash.slice(1));hash.set('view',S.view);hash.set('cohort',S.cohort);history.replaceState(null,'','#'+hash);
  }
  function setCohort(cohort,render=true) {
    if(!['main','positive_garage'].includes(cohort))return;
    S.cohort=cohort;S.comparison=null;S.interaction=null;S.profileStart=0;$('researchCohort').value=cohort;writeHash();if(render)show(S.view);else if(S.data&&S.view==='directory'){const pill=$('researchHost').querySelector('.scope-pill');if(pill)pill.textContent=meta().label+' · n = '+num(meta().transactions);}
  }
  function show(view,write=true) {
    if(!S.data)return;if(!views.some(r=>r[0]===view))view='overview';
    hideTooltip();S.view=view;S.exports.clear();
    $('researchHost').querySelectorAll('.js-plotly-plot').forEach(node=>Plotly.purge(node));
    $('researchNav').querySelectorAll('[data-view]').forEach(b=>{if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
    $('directoryPanel').hidden=view!=='directory';$('notice').textContent='';
    if(write){writeHash();requestAnimationFrame(()=>$('researchHost').scrollIntoView({block:'start',behavior:'instant'}));}
    if(view==='directory'){$('researchHost').innerHTML=heading('08','全部组目录与高维图谱','Full group directory and existing projections','查询用于解释组号：所有成员分布、具体条件与导出仍在这里。图谱中的密度是抽样显示；直方图和排序则使用全部符合筛选的组。');window.GroupDirectory.activate(S.cohort).catch(err=>{$('error').textContent=err.message;$('error').hidden=false;});return;}
    const renderers={overview,extremes,controls,interactions,algebra,validation,coverage};
    try{renderers[view]();}catch(err){$('researchHost').innerHTML='<p class="view-error">视图载入失败 / View error: '+e(err.message)+'</p>';console.error(err);}
  }
  let hideTimer=null,showTimer=null;
  function hideTooltip() {clearTimeout(hideTimer);clearTimeout(showTimer);S.hoverSerial++;S.hoverTarget?.removeAttribute('aria-describedby');S.hoverTarget=null;$('groupTooltip').hidden=true;}
  function placeTooltip(target) {
    const tip=$('groupTooltip'),box=target.getBoundingClientRect();
    tip.style.left='12px';tip.style.top='12px';
    const width=tip.offsetWidth,height=tip.offsetHeight;
    const left=Math.max(12,Math.min(box.left,innerWidth-width-12));
    const top=box.bottom+10+height<=innerHeight-12?box.bottom+10:Math.max(12,box.top-height-10);
    tip.style.left=left+'px';tip.style.top=top+'px';
  }
  function showTooltip(target) {
    clearTimeout(hideTimer);clearTimeout(showTimer);if(S.hoverTarget===target&&!$('groupTooltip').hidden)return;
    S.hoverTarget?.removeAttribute('aria-describedby');S.hoverTarget=target;const serial=++S.hoverSerial;
    showTimer=setTimeout(async()=>{
      if(!target.isConnected||serial!==S.hoverSerial)return;
      const id=target.dataset.groupId,tip=$('groupTooltip');target.removeAttribute('title');target.setAttribute('aria-describedby','groupTooltip');
      tip.innerHTML=`<strong>${e(id)}</strong><span>正在载入条件 / Loading conditions…</span>`;tip.hidden=false;placeTooltip(target);
      try {
        let row=summary(id);
        if(!row){row=await GroupQuery.request('/api/group?'+new URLSearchParams({id,cohort:id.startsWith('positive_garage-')?'positive_garage':S.cohort}));cacheRow(row);}
        if(serial!==S.hoverSerial||!target.isConnected)return;
        tip.innerHTML=`<strong>${e(row.group_id)}</strong><div class="tooltip-stats"><span>n = ${num(row.n)}</span><span>成交／估值 ${pct(row.mean_ratio)}</span></div><ul>${row.condition_list.map(c=>'<li>'+e(c)+'</li>').join('')}</ul><div class="tooltip-hint">代表条件写法 · 同成员组可能有等价写法。点击查看全部变量分布与成员。<br>Representative conditions · Click for complete details.</div>`;placeTooltip(target);
      }catch(err){if(serial===S.hoverSerial)tip.innerHTML=`<strong>${e(id)}</strong><p>${e(err.message)}</p>`;}
    },90);
  }
  function delayHide(){clearTimeout(hideTimer);hideTimer=setTimeout(hideTooltip,180);}
  document.addEventListener('pointerover',ev=>{const target=ev.target.closest?.('[data-group-id]');if(target)showTooltip(target);if($('groupTooltip').contains(ev.target))clearTimeout(hideTimer);});
  document.addEventListener('pointerout',ev=>{const target=ev.target.closest?.('[data-group-id]');if(target&&!target.contains(ev.relatedTarget)&&!$('groupTooltip').contains(ev.relatedTarget))delayHide();if($('groupTooltip').contains(ev.target)&&!$('groupTooltip').contains(ev.relatedTarget))delayHide();});
  document.addEventListener('focusin',ev=>{const target=ev.target.closest?.('[data-group-id]');if(target)showTooltip(target);});
  document.addEventListener('focusout',ev=>{if(ev.target.closest?.('[data-group-id]'))delayHide();});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape')hideTooltip();});
  window.addEventListener('scroll',ev=>{if($('groupTooltip').contains(ev.target))return;if(S.hoverTarget===document.activeElement){if(!$('groupTooltip').hidden)placeTooltip(S.hoverTarget);return;}hideTooltip();},true);
  window.addEventListener('resize',hideTooltip);
  document.addEventListener('click',ev=>{
    const group=ev.target.closest?.('[data-group-id]');if(group){ev.preventDefault();hideTooltip();window.GroupDirectory.open(group.dataset.groupId);return;}
    const view=ev.target.closest?.('[data-view]');if(view){show(view.dataset.view);return;}
    const csv=ev.target.closest?.('[data-export]');if(csv){downloadCSV(csv.dataset.export);return;}
    const svg=ev.target.closest?.('[data-image]');if(svg)Plotly.downloadImage($(svg.dataset.image),{format:'svg',filename:svg.dataset.image,width:1100,height:650});
  });
  function restoreHash(openGroup=false) {
    const hash=new URLSearchParams(location.hash.slice(1)),id=hash.get('group');
    const cohort=hash.get('cohort')||(id?.startsWith('positive_garage-')||/^G\d/.test(id||'')?'positive_garage':'main');
    S.cohort=['main','positive_garage'].includes(cohort)?cohort:'main';$('researchCohort').value=S.cohort;S.comparison=null;S.interaction=null;S.profileStart=0;
    show(hash.get('view')||'overview',false);
    if(openGroup&&id)window.GroupDirectory.open(id);else if(openGroup&&$('groupDialog').open)$('groupDialog').close();
  }
  async function init() {
    $('researchNav').innerHTML=views.map(([id,zh,en])=>`<button type="button" data-view="${id}">${zh}<small>${en}</small></button>`).join('');
    try {
      const compressed=typeof DecompressionStream!=='undefined';
      const response=await fetch(compressed?'research-data.json.gz':'research-data.json');if(!response.ok)throw new Error('Research data HTTP '+response.status);
      S.data=compressed?await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json():await response.json();
      if(S.data.schema!==1||S.data.version!==S.data.metadata.version)throw new Error('Research snapshot and group registry do not match');
      $('researchCohort').onchange=()=>setCohort($('researchCohort').value);
      restoreHash();window.addEventListener('hashchange',()=>restoreHash(true));document.documentElement.dataset.researchReady='true';
    }catch(err){$('researchHost').innerHTML='<p class="view-error">研究数据载入失败 / Research data unavailable: '+e(err.message)+'</p>';console.error(err);}
  }
  window.Workbench={cacheRow,reference:ref,show,setCohort,get view(){return S.view;},get cohort(){return S.cohort;}};
  window.Workbench.ready=init();
})();
