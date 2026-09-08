# Group Explorer v1.0.0

[Open the live workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/) · [Repository and documentation](https://github.com/BIOcanse/philadelphia-assessment-group-explorer)

The first public release provides two complete editions of the Philadelphia Assessment Group Explorer:

- **[Browser edition](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/group-explorer-browser-v1.0.0.zip)** — a static website with all group data and CSV/Parquet downloads. Queries run in a Web Worker; no Python backend is required.
- **[Local Windows x64 edition](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/group-explorer-local-windows-x64-v1.0.0.zip)** — an offline portable application with the original Python query service, all native group data, CSV/Parquet catalogs and the Excel companion. Extract the archive and run **Start.cmd**. The runtime is included; use **Stop.cmd** when finished.
- **[SHA256SUMS.txt](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.0.0/SHA256SUMS.txt)** — checksums for both archives.

Both editions use the same 7,598,906 distinct-member condition groups and the same group mean of individual sale/original-assessment ratios. Group IDs, aliases, joint conditions, all-variable distributions, ranking, histograms and filtered exports are preserved.

Data version: `groups-b5a7e308e8c6`. The interface is bilingual; repository and release documentation are in English. Full record/ranking checks, browser interaction tests and portable-runtime comparisons passed. Read the [method and interpretation](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/blob/main/docs/methodology.md) for the retained-sample scope.

GitHub's automatically generated source archives contain code and documentation. Download the named edition ZIPs above for the complete runnable datasets.
