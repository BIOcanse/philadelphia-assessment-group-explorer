# Philadelphia Assessment Group Explorer

Explore **7,598,906 condition groups** to see where average sale prices differ from the original property assessments. Look up a group ID, read its joint conditions, rank group means, and inspect the complete filtered histogram.

**[Open the interactive workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/)** · **[Releases](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases)** · **[Example: M025](https://biocanse.github.io/philadelphia-assessment-group-explorer/#group=main-03600322)**

## Two editions

Both editions are maintained. They share group identifiers, the bilingual interface, and the same statistics.

| Edition | Download | How it runs |
| --- | --- | --- |
| Browser / GitHub Pages | [Browser edition v1.0.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/group-explorer-browser-v1.0.0.zip) | Static files; all queries run in a browser Web Worker. No Python backend. |
| Local / Windows x64 | [Portable local edition v1.0.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/group-explorer-local-windows-x64-v1.0.0.zip) | Extract and run **Start.cmd**. Python and dependencies are included. Works offline. |

[SHA-256 checksums](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/SHA256SUMS.txt) · [Local edition instructions](docs/local-edition.md) · [Browser edition instructions](docs/browser-edition.md)

The local edition retains the Excel group dictionary, CSV exports, full Parquet catalogs, and the Python query API. The browser edition provides CSV and Parquet downloads. The complete data is included in both release packages; a source checkout alone does not contain the datasets.

## What you can do

- Enter a canonical ID such as `main-03600322`, a candidate alias such as `M025` or `G025`, or a full-profile ID such as `M-P001029`.
- Read representative joint conditions and all conditions shared by the group's members.
- Inspect every variable's category distribution, member counts, and sale/assessment means.
- Rank groups from high to low, low to high, or by transaction count.
- Filter by minimum transaction count, percentage range, and combined category conditions.
- Click a histogram bin or a plotted point to inspect the corresponding groups.
- Export the applied filter to CSV, or download complete Parquet catalogs.

The default `n >= 100` browser catalog is exact, not sampled. Selecting a lower threshold loads the full catalog for that cohort. The histogram counts **all matching groups**. The PCA/t-SNE view is separately labelled as a 1,320-group sampled atlas for each cohort.

## What the numbers mean

The primary measure is the **arithmetic mean of each transaction's sale price divided by its original assessment**. A mean of 114% means that the group's average individual ratio is 14 percentage points above 100%. It is not the ratio of total sale prices to total assessments.

| Cohort | Transactions | Fields | Distinct non-baseline groups |
| --- | ---: | ---: | ---: |
| Main | 4,903 | 20 | 5,550,736 |
| Positive garage | 2,148 | 21 | 2,048,170 |

Different condition expressions with identical members share one group ID. The unrestricted cohort baseline can be looked up but is excluded from condition-group counts. The cohorts overlap, so the total does not represent independent observations or independent bias mechanisms.

Data version: `groups-b5a7e308e8c6`. IDs remain stable for this version; sorting and filtering do not renumber them. Read the [method and scope](docs/methodology.md) before interpreting the results.

## Development and publication

`workbench/static/` contains the shared interface and local API client. `workbench/pages/` contains the browser client and Worker. The local query implementation is in `workbench/catalog.py`, `workbench/server.py`, and `scripts/`. Release data lives in GitHub Releases rather than Git history.

The Pages workflow deploys the verified browser ZIP from the published release. [Deployment instructions](docs/browser-edition.md) explain how to host the same artifact elsewhere. [Validation evidence](docs/validation.md) records the checks used for this release.

This is an independent research workbench, not a government valuation service. The underlying historical sales data comes from the [University of Chicago Property Tax Project's Philadelphia replication materials](https://propertytaxproject.uchicago.edu/philadelphia-raw-data-code/). Derived group statistics describe the retained samples; the interface does not establish causal effects or citywide representativeness. Third-party component notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
