# Method and interpretation

For a group G, the displayed measure is `mean(sale_price_i / original_assessment_i)` over its member transactions. The table ranks this group mean. It does not rank individual properties or use a ratio of sums. A 100% mean is the reference level.

The retained main cohort has 4,903 transactions and 20 fixed categorical fields. The positive-garage cohort has 2,148 transactions and 21 fields. Conditions are conjunctions of category restrictions. Condition expressions with the same members have the same canonical ID; the resulting catalogs contain 5,550,736 and 2,048,170 non-baseline groups. Counting every equivalent expression is a different unit and produces different histogram frequencies.

The representative expression is reduced by removing redundant conditions without changing members. It is not claimed to be uniquely or globally shortest. The detail panel also exposes the full set of shared conditions and distributions of all variables, including variables not fixed by that expression.

The study uses historical Philadelphia sales and assessment replication data, with geographically linked historical school, employment and police-report information. Original amounts, cohort membership, category boundaries and the established source-version checks are preserved in this release. Historical information is used where available; assessment-year and attribute-timing limitations remain. Police-report counts measure recorded reports within the defined period and distance, not a direct measure of personal safety. Research category boundaries are not official ratings unless explicitly labelled as such. Gated-community status was not established.

Coverage depends on information availability and varies with price. Results must therefore remain scoped to the corresponding retained cohort. The positive-garage cohort overlaps the main cohort. Overlapping groups are not independent tests or distinct mechanisms, and an extreme group mean alone does not identify a cause. The site supports inspecting descriptive patterns and research candidates; it does not assert government endorsement, a new validated valuation model, or generalization to unobserved years.

The histogram includes every matching distinct-member group. The existing PCA/t-SNE atlas contains 1,320 sampled/focus groups per cohort; its visual density must not be interpreted as the population's group frequency.

Version: `groups-b5a7e308e8c6`. Group IDs are version-specific, and sorting/filtering preserves those IDs. Lookup aliases `M025` and `G025` resolve to `main-03600322` and `positive_garage-01724426`. Full-profile aliases use `M-P` and `G-P`; unqualified `P` aliases use the currently selected cohort.

Source context: [University of Chicago Property Tax Project — Philadelphia raw data and code](https://propertytaxproject.uchicago.edu/philadelphia-raw-data-code/).
