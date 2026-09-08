# Research Story v1.2.0

[Read the research story](https://biocanse.github.io/philadelphia-assessment-group-explorer/research-story.html) · [Open the full workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/)

This release adds a separate, bilingual research narrative. It reconnects the original assessment-regressivity question with the completed group research, without replacing the eight workbench views or changing their underlying results.

- Four interactive charts explain the price gradient, residual group counts, a four-cell interaction, and direct out-of-fold ratio R².
- New statistics distinguish raw-price Pearson correlation, in-sample log-price R², proportionality tests, and direct ratio prediction R² from the previous calibration-loss improvement metric.
- The 2017 retained sample contains 8,595 unique parcel IDs, so annual parcel deduplication changes nothing. Cluster-based proportionality inference remains conditional on the selected source data.
- Conclusions include negative predictive findings, unresolved assessment timing and selection, and a concrete plan for independent validation.
- Downloadable report evidence includes the canonical artifact, derived tables, Python builder, validation and a base-R reproduction script. Python and QR cross-checks were executed; the R script has not been executed in this environment.

## Two complete editions

- [Browser edition v1.2.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.2.0/group-explorer-browser-v1.2.0.zip): static site with Web Worker queries, all group data and the self-contained research story.
- [Local Windows x64 edition v1.2.0](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.2.0/group-explorer-local-windows-x64-v1.2.0.zip): extract and run Start.cmd; the local Python/NumPy service, runtime, Excel companion and all data are included.
- [SHA256SUMS.txt](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.2.0/SHA256SUMS.txt).

The group-data version remains groups-b5a7e308e8c6. Earlier releases remain available. Use the named edition ZIPs for runnable packages; GitHub source archives alone do not include all datasets.
