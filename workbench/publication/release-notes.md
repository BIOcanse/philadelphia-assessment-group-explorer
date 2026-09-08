# Formula Validation v1.4.0

[Read the research story](https://biocanse.github.io/philadelphia-assessment-group-explorer/research-story.html) · [Full workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/)

The separate research story now reports completed validation of our algebraic formula and the method that derives it. Scores compare predicted and observed GROUP arithmetic means of sale/original-assessment ratios.

- 30 real-data experiments cover nested training fractions, train-only degree selection through all 20/21 fields, and profile, spatial, and chronological holdouts. 180 known-answer settings test additive and higher-order signals, noise, and unseen states.
- In the main fixed holdout, the prespecified additive formula achieves r = 0.774, predictive R² = 0.508 and RMSE = 1.37 percentage points on 74 eligible single-field groups. The original unregularized degree-three formula has R² = −0.425.
- All 7,598,906 existing canonical groups were scanned against their held-out members. Among 132,602 main-sample groups with distinct test membership and at least 30 test transactions, additive and degree-three R² are 0.376 and −0.261. This is a separate group-scoring family; overlapping groups are not independent evidence.
- Explicit-design checks support the mathematical equivalence. Known four-way signals can be recovered when training support identifies them. Exact reconstruction and greater complexity do not guarantee stable prediction; joint gains vary across splits. Regularization and more stable training-only selection are proposed next steps, not completed improvements.
- Eight figures and three tables show findings, learning curves, transfer scores, and known-answer experiments. The evidence ZIP includes saved formulas, split records, scores, source checks, and an executed audit notebook. Desktop rendering, source interaction, and independent numerical validation passed.
- Original analyses, workbench tools, data, and group IDs are preserved. Findings remain internal to the retained historical samples; they do not establish causal effects or citywide generalization.

Both complete editions are maintained:

- [Browser edition v1.4.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/group-explorer-browser-v1.4.0.zip)
- [Local Windows x64 edition v1.4.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/group-explorer-local-windows-x64-v1.4.0.zip)
- [Checksums](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/SHA256SUMS.txt)

The archives update three publication files per edition in the verified v1.2.0 base packages: the story, its evidence ZIP, and the README. All other members are preserved and individually verified; they are also unchanged in v1.3.0. The local edition includes its runtime and full data. Prior releases remain available.
