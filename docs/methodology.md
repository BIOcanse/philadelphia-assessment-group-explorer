# Method and interpretation

For a group G, the displayed measure is `mean(sale_price_i / original_assessment_i)` over its member transactions. The table ranks this group mean. It does not rank individual properties or use a ratio of sums. A 100% mean is the reference level.

The retained main cohort has 4,903 transactions and 20 fixed categorical fields. The positive-garage cohort has 2,148 transactions and 21 fields. Conditions are conjunctions of category restrictions. Condition expressions with the same members have the same canonical ID; the resulting catalogs contain 5,550,736 and 2,048,170 non-baseline groups. Counting every equivalent expression is a different unit and produces different histogram frequencies.

The representative expression is reduced by removing redundant conditions without changing members. It is not claimed to be uniquely or globally shortest. The detail panel also exposes the full set of shared conditions and distributions of all variables, including variables not fixed by that expression.

The study uses historical Philadelphia sales and assessment replication data, with geographically linked historical school, employment and police-report information. Original amounts, cohort membership, category boundaries and the established source-version checks are preserved in this release. Historical information is used where available; assessment-year and attribute-timing limitations remain. Police-report counts measure recorded reports within the defined period and distance, not a direct measure of personal safety. Research category boundaries are not official ratings unless explicitly labelled as such. Gated-community status was not established.

Coverage depends on information availability and varies with price. Results must therefore remain scoped to the corresponding retained cohort. The positive-garage cohort overlaps the main cohort. Overlapping groups are not independent tests or distinct mechanisms, and an extreme group mean alone does not identify a cause. The site supports inspecting descriptive patterns and research candidates; it does not assert government endorsement, a new validated valuation model, or generalization to unobserved years.

The directory histogram includes every matching distinct-member group. The exhaustive histogram in **Group extremes** uses all supported concrete condition expressions for orders 1 through d: 1,749,843,543 main and 1,671,325,525 garage expressions. Equivalent member sets are counted again in that view. The existing PCA/t-SNE atlas contains 1,320 sampled/focus groups per cohort; its visual density must not be interpreted as the population's group frequency.

The overview price-band chart preserves the original exploration of 8,595 transactions in 2017. It displays transaction medians and interquartile ranges, explicitly separate from the condition-group arithmetic means used elsewhere.

Original ratio gaps, differences from the cohort mean in percentage points, and ratios divided by the cohort mean are distinct measures. The workbench labels each basis. Conditional standardization compares an original group with newly admitted members of its relaxed parent, using only common strata. Missing common support remains unavailable, never zero. Changing support can itself change the observed comparison.

Four-cell interactions use `r11 - r10 - r01 + r00`. Adjusted contrasts, saved maxT references and fixed-prediction bootstrap intervals are exploratory internal evidence. They are not independent confirmation or causal identification. Model-validation gains are relative MSE percentages; ratio RMSE and reconstruction error are reported in percentage points.

The exact algebra stores counts and ratio sums on 3,310 main and 1,449 garage observed complete profiles. A condition group is an indicator selection of profiles, and its mean is the selected ratio sum divided by the selected count. Degree three reaches full numerical rank on this observed support. This is interpolation capacity, not proof that the underlying assessment mechanism has only third-order interactions or that future predictions are accurate. The kernel window uses actual category agreement counts; the weighted option displays `sqrt(n_i) K_ij sqrt(n_j)`.

The downloadable research snapshot records each input's SHA-256 hash and a chart-to-source map. Its builder resolves every four-cell group to the native registry and reconciles cell sizes and means, control decompositions, exhaustive expression counts and profile totals. No model was refitted for the workbench integration.

Version: `groups-b5a7e308e8c6`. Group IDs are version-specific, and sorting/filtering preserves those IDs. Lookup aliases `M025` and `G025` resolve to `main-03600322` and `positive_garage-01724426`. Full-profile aliases use `M-P` and `G-P`; unqualified `P` aliases use the currently selected cohort.

Source context: [University of Chicago Property Tax Project — Philadelphia raw data and code](https://propertytaxproject.uchicago.edu/philadelphia-raw-data-code/).
