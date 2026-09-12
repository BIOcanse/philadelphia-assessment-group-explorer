# Individual Training Study v1.5.0

[Read the research story](https://biocanse.github.io/philadelphia-assessment-group-explorer/research-story.html) · [Full workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/)

This release adds 18 matched internal experiments with individual-transaction training, continuous features, regularization and individual-error selection. Predictions are aggregated over held-out members of the original condition groups. Binned inputs, marginal-group selection and nonlinear additive formulas remain explicit comparators.

The fitted all-order kernel equation is saved with its parameters and coefficients. It provides partial predictive structure, not a recovered universal law. Previously inspected test sets make this retrospective internal validation.

- The main fixed holdout gives individual R² 0.077, single-field group R² 0.489 and pair-group R² 0.478 for the continuous, individual-selected equation.
- All 7,598,906 canonical groups were rescored. Across 132,602 main groups with distinct held-out membership and at least 30 test transactions, R² is 0.429 versus 0.396 for the continuous additive comparator. These are overlapping groups, not independent samples.
- Single/pair group metrics additionally require at least two supported groups per partition. The two scoring families have different weights and denominators.
- The bilingual narrative includes chosen kernel parameters, matched comparisons, learning curves, transfer scores and residual-group links with condition tooltips.
- The evidence bundle contains saved equations, splits, individual predictions and independent validation scripts. The preceding stage's evidence ZIP, including its audit notebook, is retained inside it.
- Original analyses, 30 previous experiments, 180 known-answer settings, workbench tools and group IDs are preserved. Findings do not establish causal effects or citywide generalization.

Both complete editions are maintained:

- [Browser edition v1.5.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.5.0/group-explorer-browser-v1.5.0.zip)
- [Local Windows x64 edition v1.5.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.5.0/group-explorer-local-windows-x64-v1.5.0.zip)
- [Checksums](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.5.0/SHA256SUMS.txt)

The archives update three publication files per edition in the verified v1.2.0 base packages: the story, evidence ZIP and README. Other members are preserved and individually verified. The local edition includes its runtime and full data. Prior releases remain available. See the [protocol](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/blob/main/docs/raw-feature-formula.md) and [results](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/blob/main/docs/raw-feature-formula-results.md).
