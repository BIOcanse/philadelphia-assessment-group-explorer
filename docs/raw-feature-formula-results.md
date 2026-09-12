## 当前结论 · 训练对象改到逐笔之后，规律仍然只有部分可预测 / Current finding

**这轮已经跑完：18套相同划分的对照、逐笔学习与选模、连续变量、正则化，以及任意阶组目录验证。仍未得到“小部分样本学会、对其余样本优秀拟合”的公式。**

主样本用3,943笔训练、960笔留出：逐笔预测R²=0.077；单变量组R²=0.489；双变量组R²=0.478；任意阶组R²=0.429。这些是不同粒度的指标，不能混为一个准确率。组评分均要求至少30笔留出交易；单/双变量还要求每个分区至少两个合格组。

联合流程在18套双变量组比较中有14套误差更低、1套相同，显示进一步研究的价值；但改进幅度有限，也还没有不确定性检验来确认稳定优势。下面先讲本轮结果；此前研究完整保留在后半部分。返回[完整研究工作台](./index.html#view=overview)，或下载[方程、预测和审计来源包](./research-story-sources.zip)。

The completed comparison finds partial predictive structure, not a recovered universal law. Individual R² and group-mean R² answer different questions. Earlier analyses remain available below and in the workbench.


## A · 这次究竟改了什么 / What changed

每笔房屋的目标始终是 qᵢ=成交价ᵢ／原估值ᵢ。**用训练交易学习公式 → 对未参与训练的交易逐笔预测 → 按原条件分组 → 比较预测均值和实际均值。** 不用成交价格或价格档作为预测变量。

原方法将“所有分档条件完全相同”的记录合并，并按记录数加权，其平方误差拟合已经与逐笔训练等价。本轮真正改变的是：保留连续数值、允许正则化，以及用逐笔验证误差选模型；同一候选池也按旧的单变量组误差选一次，形成对照。

两个样本、原20/21个字段和原划分都保留。小训练量为开发池50%：主样本1,972笔、车库858笔；大训练量为3,943/1,717笔。每种训练量用三个种子，另做完整组合、空间网格和内部时间留出，总共18套。现有测试结果早已被查看过，因此这是**内部回顾验证**，不是新的盲测。

Training uses individuals; evaluation aggregates only held-out predictions and outcomes over identical group members. The old identical-profile compression was loss-equivalent. This study tests feature resolution, regularization and selection, with matched splits and no new exclusions.


## B · 现在得到的矩阵与方程 / The fitted equation

**α=(K+nλI)⁻¹(q−μ)，q̂(x)=μ+k(x,X)ᵀα。** μ为训练成交比率均值，λ是只在训练内部选择的正则化强度。保存的NPZ包含α、训练点、标准化参数及所有核参数，可以重新逐笔计算预测。

每个字段先形成相似度 bⱼ：连续变量用高斯相似度，邮编用是否同类。加性核为 Kₐ=Σⱼbⱼ/d；联合核为 Kⱼ=∏ⱼ(1+τbⱼ)/(1+τ)ᵈ。后者等于 **Σₛ τ^|S|∏ⱼ∈ₛbⱼ/(1+τ)ᵈ**，S遍历包括空集在内的全部字段子集。因此一阶直到20/21阶都在表达中，计算不需要逐项展开数百万组合。

但各阶权重受到这个核的结构约束，λ控制拟合复杂度。允许全部阶数不等于已经识别出必须存在的20阶作用。加性对照允许单变量弯曲关系；它不是只画一条直线的弱基准。

The saved kernel-ridge equation includes all interaction orders through a product expansion. It is a structured, regularized family, not an unrestricted proof of the true interaction order. The additive comparator allows nonlinear single-feature functions.


## C · 更细的信息有没有带来提升 / Did the changes help?

下表将“分档／连续”与“组误差／逐笔误差选模”分开，所有行使用同一固定留出成员。逐笔误差以百分点计；R²是1−预测平方误差／实际组均值方差，越高越好，负值意味着比直接用测试均值还差。

主样本连续逐笔选模的单变量组 r=0.739，R²=0.489，RMSE=1.39个百分点；双变量组R²=0.478。同样连续输入的加性对照分别为0.491和0.502。**对照的差异有限，不能宣称已经抓到了此前遗漏的大量高阶规律。**

Compare both calibration and correlation. A higher r alone does not establish a better equation. These pipeline comparisons also change applicable similarity functions and candidate grids; they do not isolate binning as a causal treatment.


## D · 数据加倍后是否更稳定 / Learning and transfer

下图把主样本训练量从1,972增加到3,943笔，始终预测相同960笔留出交易的双变量组均值。线为三个种子的均值，来源表保留最小值、最大值；它们共享测试集，不能当作三份独立证据。

合计18套比较中，“允许联合项并按逐笔选模”的双变量组误差低于连续加性对照的有14套，数值相同1套，其余更高。选到加性时，两者本来就是同一个模型；选到联合核也不能直接推出作用阶数。改善是否稳定，比某一套里谁略胜更重要。

Learning curves use held-out outcomes only. Seed variation is sensitivity to training and selection, not a confidence interval or independent replication.


## E · 最后仍然回到具体组 / Return to identifiable groups

任意阶目录重新检查了7,598,906个正式组。去除空测试组并按测试成员去重后，n≥30的主样本组有132,602个、车库组45,285个；它们仍然大量重叠。连续逐笔选模在这两批组上的R²分别为0.429、0.316。

下图每个点为一个主样本单变量留出组，横轴为实际成交／估值组均百分比，纵轴为预测误差（百分点）。悬停数据可查条件，下面的正式组号还可直接返回原工作台。编号相同，但工作台的完整组统计与这里的留出成员统计有不同分母。

The complete catalog is evaluated by summing individual predictions, including variation within old bins. Overlapping group counts are descriptive coverage, not independent sample sizes.


本轮按任意阶组测试误差选出的探索例子：[main-02124043](./index.html#group=main-02124043)（测试n=32，误差+11.38个百分点）；[main-04783053](./index.html#group=main-04783053)（测试n=39，误差+10.79个百分点）。悬停编号显示条件；这些组已按结果筛选，不能再视作独立确认。

These post-test residual examples are exploratory. Hover an ID for conditions; click for the original group.

## 接下来该解决什么 / Next research decision

这轮排除了一个简单解释：问题并不只是“拿组均值训练”或“没有允许高阶”。保留连续信息、逐笔选模、允许全部阶数之后，仍没有出现全面优秀的留出拟合。当前证据不支持把一个模型直接称为真解。

下一步应固定这轮保存的预测，先分清**组均值本身的抽样波动有多大，剩余误差是否还有可重复结构**。用按房屋重采样的成对误差区间比较加性与联合公式；重叠组要一起随房屋重采样，不能把数十万组当成独立样本。再通过交叉拟合检查残差与联合条件的关系，诊断应与最终确认分开。

如果残差结构能复现，再针对性检验更灵活的核相似度、正则化选择或已有字段的语义问题，并用独立时期数据确认；如果没有，继续无目的扩大阶数并不能区分噪声和缺少信息。此次尚未执行上述不确定性与残差检验。

Next, quantify paired uncertainty by resampling transactions, then test whether residual structure repeats under cross-fitting. Preserve joint group membership in resampling. This determines whether another richer equation is warranted; it has not yet been executed.


## 使用边界与核验 / Scope and verification

18套实验的划分、模型选择、保存方程逐笔重算以及组均值、r、R²均已核验。全阶扫描的交易数与原目录逐组一致，另对每个样本40个固定抽取的任意阶组直接重算成员；这40项是抽查，不声称独立逐组重算了全部预测。

单/双变量评分沿用旧规则：先要求组内最少交易数，再保留至少两个合格组的分区，分区等权、分区内组等权。全阶目录按独特测试成员组等权。两者不是同一指标。原楼层字段仍是语义有疑点的代理（主样本最大值52），未擅自裁剪为“正常楼层”。房屋属性快照、当前坐标代理、历史评分及估值年份口径等限制仍在；可得性与价格相关的样本结论不得推广到整体，更不能据预测相关性宣称因果来源。

Independent validation covers all stored predictions and supported group scores. Historical snapshots, feature semantics, selected-sample scope and previously inspected holdouts limit interpretation. No claim of causal identification or external validation is made.


## 前一阶段研究与证据 / Earlier research retained

以下是v1.4阶段的研究过程、无正则公式验证和已知答案实验。数字与原分析保持一致；其中“当前”“下一步”措辞以本页上方本轮结论为准。此前完整报告和方程证据也保留在下载包的previous_formula_evidence.zip中。

The following material preserves the preceding stage. Its historical status language is superseded by the new experiment above; its measured results are unchanged.
