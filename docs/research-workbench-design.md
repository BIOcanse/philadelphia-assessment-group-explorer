# Research workbench implementation

## Intent and selected surface

Extend the existing published bilingual application into a research workbench. The entry point explains and explores the completed analysis; group lookup is supporting infrastructure. Preserve the local Python/NumPy service and the independent static Web Worker edition, sharing the same interface and research snapshot. This is an extension of the user's chosen software application, not a new standalone report runtime. Native Plotly views retain the existing interaction model; source reports remain the evidence behind the snapshot.

## Reader workflow

1. **Overview:** metric definition, separate sample scopes, the original price-band exploration, and links into each research question.
2. **Extremes:** full condition-expression histogram by order, support versus attainable group means, and the one-variable / all-but-one-variable extremes. Distinguish expression counts from distinct-member group counts.
3. **Conditional comparisons:** select a candidate and a removed condition; compare original group, relaxed parent and newly admitted transactions. Show common-support retention and standardized contrasts for the four existing control schemes.
4. **Interactions:** browse the existing four-cell scans, with field and support filters, a selectable interaction, its four group means and the non-additive contrast. Reference eligibility and internal uncertainty stay visible.
5. **Algebra:** explore the saved order/rank/error results and a real profile-kernel submatrix. Explain exact count-and-sum aggregation, sparse support, and interpolation versus prediction.
6. **Validation:** compare saved spatial and forward validation results with their fixed-prediction descriptive intervals. Do not refit models or imply independent confirmation.
7. **Data coverage:** show availability across price bands and historical source scope. Missing values remain unavailable; conclusions stay within the observed cohorts.
8. **Group directory:** preserve complete queries, ranking, exports, member records, and projections. Open group detail from every research view without losing that view.

## Data and interaction contracts

- The main metric is the arithmetic mean of individual sale/original-assessment ratios, expressed as a percentage. The overview's original price-band chart is explicitly a transaction median with an interquartile range.
- Build one compact, deterministic `research-data.json` from existing CSV/JSON evidence. Include source paths, SHA-256 hashes, row counts, metric units, and a chart-to-source map. Build validation reconciles exported rows and every linked group against the fixed registry.
- Map expression-specific IDs and four-cell conditions to canonical distinct-member IDs with the saved sorted closure index. Never treat an expression ID as a registry ID.
- A shared group-reference component displays representative conditions, sample size and the original mean on hover or keyboard focus. A click opens full detail in an accessible drawer; Escape closes the drawer/tooltip. Native plot hover labels contain the same concrete group information.
- Cached evidence summaries make research-page hovers immediate; arbitrary directory IDs use the existing query interface. Bound the cache and guard asynchronous responses against stale hover/selection state.
- Research views load before the large group directory. Both editions use relative asset paths. Existing `#group=...` links remain valid, and view/cohort state is shareable.

## Implementation boundaries and validation

Add a shared research module and style layer, a snapshot builder/validator, and explicit publication/static-server allowlists. Reuse the existing query clients and exact catalogs. Do not introduce another server, framework, fitting pipeline, or second group-ID scheme.

Verify source reconciliation, support counts, group mappings, original versus calibrated units, reference eligibility, null handling, and matrix values. Exercise all views, filters, cross-view group navigation, hover/focus behavior, hash restoration and delayed-request races in both editions. The user's latest scope prioritizes PC use exclusively: validate desktop layouts at 1440 and 1200 pixels and favor readable charts, tables and keyboard/mouse workflows. No further phone-layout work or phone acceptance criteria. Publish a new release containing both complete editions and retain v1.0.0.

## Delivered v1.1.0

Application commit: `056ecf4d2d77af1f301ec88fda19a165d30b81c7`. Release: https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/tag/v1.1.0 . Live site: https://biocanse.github.io/philadelphia-assessment-group-explorer/ . Both complete editions and v1.0.0 are retained. The original local service at port 8767 is updated; temporary validation services on 8770/8771 were stopped.

The snapshot links 9,199 cited native groups, 4,802 four-cell comparisons and 1,920 control comparisons. Local/static/live desktop suites passed 64/65/65 checks, plus nine delayed-response checks and 584 export-value checks per surface. Fresh portable extraction passed 11 boot/asset/query checks. Uploaded hashes, anonymous download links and live asset bytes match. Canonical evidence: `outputs/research_workbench/workbench-validation.json` and `publication-validation.json`.
