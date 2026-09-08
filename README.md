# Philadelphia Assessment Research Workbench

**[Read the research story](https://biocanse.github.io/philadelphia-assessment-group-explorer/research-story.html)** — a separate guide to observed combination bias, the exact algebraic representation, and completed held-out validation of that formula and its derivation method. It includes 30 real-data experiments, 180 known-answer settings, learning curves, transfer checks, and group-level prediction scores. The original workbench views and results remain available.

The mathematical representation passes explicit-design equivalence checks, but exact reconstruction does not guarantee stable prediction. In the main sample's fixed holdout, the prespecified additive formula reaches **r = 0.774, predictive R² = 0.508, RMSE = 1.37 percentage points** on 74 eligible single-field groups; the original unregularized degree-three formula has R² = −0.425. Across **132,602 distinct held-out-member groups of arbitrary order** with at least 30 test transactions, their R² values are 0.376 and −0.261 respectively. These are different scoring families, not independent populations. Joint-model gains vary across splits; stabilization is the next proposed experiment, not an already validated improvement. [Results and scope](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/blob/main/docs/formula-validation-results.md) · [Frozen pre-execution protocol](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/blob/main/docs/formula-validation.md)

Explore the completed research on assessment gaps through eight connected views: an overview, extreme groups, conditional comparisons, four-cell interactions, matrix algebra, model validation, data coverage, and the complete group directory. The workbench connects the results to **7,598,906 condition groups**. Hover or focus a group ID to see its conditions and statistics; click to inspect all variables and members without leaving the analysis.

**[Open the interactive workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/)** · **[Releases](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases)** · **[Example: M025](https://biocanse.github.io/philadelphia-assessment-group-explorer/#group=main-03600322)**

## Two editions

Both editions are maintained. They share group identifiers, the bilingual interface, and the same statistics.

| Edition | Download | How it runs |
| --- | --- | --- |
| Browser / GitHub Pages | [Browser edition v1.4.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/group-explorer-browser-v1.4.0.zip) | Static files; all queries run in a browser Web Worker. No Python backend. |
| Local / Windows x64 | [Portable local edition v1.4.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/group-explorer-local-windows-x64-v1.4.0.zip) | Extract and run **Start.cmd**. Python and dependencies are included. Works offline. |

[SHA-256 checksums](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.4.0/SHA256SUMS.txt) · [Local edition instructions](docs/local-edition.md) · [Browser edition instructions](docs/browser-edition.md)

The local edition retains the Excel group dictionary, CSV exports, full Parquet catalogs, and the Python query API. The browser edition provides CSV and Parquet downloads. The complete data is included in both release packages; a source checkout alone does not contain the datasets.

## What you can do

- Compare the lowest and highest group means at different support thresholds, inspect all edge-group ties, and explore the exhaustive condition-expression histogram by order.
- Relax a condition in any of 80 existing candidates. Inspect the original group, its parent, newly admitted transactions, common-support retention, and all four control specifications across 1,920 saved comparisons.
- Filter the 4,802 existing four-cell comparisons, inspect the four actual groups, and compare observed joint means with additive expectations and adjusted residuals.
- Change the algebra degree and reconstruction tolerance; explore a movable 24-by-24 window of the actual profile kernel and download its values.
- Compare spatial and forward predictive validation, including negative results and internal descriptive intervals. Inspect information coverage across price bands and assessment-denominator compatibility.
- Read the separate formula-validation story with eight figures and three tables. Download fitted equations, split records, scores, and an executed audit notebook from its evidence ZIP. These formula scores are distinct from the older workbench's model-validation view.
- Export each research chart's data as CSV and figures as SVG. Download the original evidence tables and the source-hashed research snapshot.
- Enter a canonical ID such as `main-03600322`, a candidate alias such as `M025` or `G025`, or a full-profile ID such as `M-P001029`.
- Read representative joint conditions and all conditions shared by the group's members.
- Inspect every variable's category distribution, member counts, and sale/assessment means.
- Rank groups from high to low, low to high, or by transaction count.
- Filter by minimum transaction count, percentage range, and combined category conditions.
- Click a histogram bin or a plotted point to inspect the corresponding groups.
- Export the applied filter to CSV, or download complete Parquet catalogs.

Research views load from a compact snapshot before the group directory is needed. The directory's default `n >= 100` browser catalog is exact, not sampled. Selecting a lower threshold loads the full catalog for that cohort. Its histogram counts **all matching distinct-member groups**. The separate exhaustive histogram counts **all supported condition expressions**, including equivalent member sets. The PCA/t-SNE view is labelled as a 1,320-group sampled atlas for each cohort.

## What the numbers mean

The primary measure is the **arithmetic mean of each transaction's sale price divided by its original assessment**. A mean of 114% means that the group's average individual ratio is 14 percentage points above 100%. It is not the ratio of total sale prices to total assessments.

| Cohort | Transactions | Fields | Distinct non-baseline groups |
| --- | ---: | ---: | ---: |
| Main | 4,903 | 20 | 5,550,736 |
| Positive garage | 2,148 | 21 | 2,048,170 |

Different condition expressions with identical members share one group ID. The unrestricted cohort baseline can be looked up but is excluded from condition-group counts. The cohorts overlap, so the total does not represent independent observations or independent bias mechanisms.

Data version: `groups-b5a7e308e8c6`. IDs remain stable for this version; sorting and filtering do not renumber them. Read the [method and scope](docs/methodology.md) before interpreting the results.

## Development and publication

`workbench/static/` contains the shared interface and local API client. `research.js` renders the completed research and shared group explanations. `workbench/pages/` contains the browser client and Worker. The local query implementation is in `workbench/catalog.py`, `workbench/server.py`, and `scripts/`. Release data lives in GitHub Releases rather than Git history. The research snapshot builder reads the original research workspace's verified outputs; it does not refit models. [Design and data contracts](docs/research-workbench-design.md) describe the integration.

The Pages workflow deploys the verified browser ZIP from the published release. [Deployment instructions](docs/browser-edition.md) explain how to host the same artifact elsewhere. [Validation evidence](docs/validation.md) records the checks used for this release.

This is an independent research workbench, not a government valuation service. The underlying historical sales data comes from the [University of Chicago Property Tax Project's Philadelphia replication materials](https://propertytaxproject.uchicago.edu/philadelphia-raw-data-code/). Derived group statistics describe the retained samples; the interface does not establish causal effects or citywide representativeness. Third-party component notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
