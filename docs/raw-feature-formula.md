# Individual training, continuous information, and group validation

Frozen before fitting, 2026-09-12. This is a retrospective internal comparison;
the existing holdouts have already been inspected in previous research.

## Question and estimand

Can a regularized kernel equation trained on individual sale/original-assessment
ratios predict held-out group arithmetic mean ratios? Does preserving continuous
information or replacing marginal-group selection with individual-error selection
improve this prediction? Existing historical analyses remain immutable.

The previous weighted identical-profile fit was already equivalent to individual
squared-error training for its binned predictors. The changes here concern feature
resolution, regularization, and hyperparameter selection, not a correction from
overlapping-group training to individual training.

## Data and exclusions

Use exactly the existing main (4,903) and positive-garage (2,148) cohorts and their
20/21 fields. Map fields through bin_definitions.json; replace school tiers with
the corresponding spr_asof_grade{1,6,9}_score100 values. These are the prior
as-of-publication score versions used to define the groups, not a new school policy.
ZIP remains categorical. Do not add sale price, assessment, ratio, price bands,
current assessment, source-year match status, or other response proxies.
Assert unique record/parcel IDs, exact response alignment and finite input values.
No added imputation or cohort exclusion. Source snapshots, coordinates, jobs and
school-boundary timing retain all existing caveats; claims apply only to the
observed available-data cohorts, not Philadelphia generally or causal effects.

For raw inputs, apply log1p to area, cityhall distance, jobs density, the four crime
counts, and garage count. Other numeric fields retain their numeric values.
Center and scale numeric inputs using training mean and standard deviation only;
zero training variance uses scale 1. Binned inputs remain nominal categories.

## Equation and predeclared candidates

Let q_i = sale_i / assessment_i and mu = training mean(q).
For numeric field j, b_j(x,u)=exp(-(z_j(x)-z_j(u))^2/(2 ell^2)); categorical
fields use equality. Define:

    K_add(x,u) = mean_j b_j(x,u)
    K_joint(x,u;tau) = product_j (1 + tau*b_j(x,u)) / (1+tau)^d
    alpha = (K(X,X) + n*lambda*I)^(-1) (q - mu)
    prediction(x) = mu + K(x,X) alpha

The product expands into every interaction order 0..d. This is an all-order
regularized family, not proof that any particular high-order effect is required.
Its additive control permits nonlinear single-feature effects but no joint terms.

Families: additive, joint tau=0.1, joint tau=1. Raw ell in {0.5,1,2}; bins use
equality (no length scale). Lambda in {1e-6,1e-5,1e-4,1e-3,1e-2,0.1,1}.
One fit grid supplies two selections: individual validation RMSE and the old
single-field group RMSE (minimum validation n=5, partition-balanced weights).
Candidate order breaks numerical ties (within 1e-10 pp): additive first, tau=0.1
before 1, ell ascending; strongest regularization first within each kernel.
Also retain the row-selected additive-only model for each representation and a
training-mean baseline. No new test-dependent candidate changes.

The four principal roles are bins/group-selection, bins/row-selection,
raw/group-selection, raw/row-selection. Input changes also change the applicable
kernel similarities and length-scale grid, so interpret this as a representation
pipeline comparison, not an isolated estimate of binning's causal effect.
Old unregularized results are historical benchmarks, not an otherwise-identical
regularization ablation. Within-family additive-vs-joint comparisons are primary
evidence for the predictive value of joint structure.

## Splits and learning curves

Reuse saved splits from formula_validation verbatim: seeds 20260908/09/10,
50% and 100% of development data, and the existing profile/spatial/time holdouts
at seed 20260908. Total: 18 cases (9 per cohort). The main random training sizes
are 1,972 and 3,943, with 960 fixed test transactions; garage 858 and 1,717,
with 431 fixed test transactions (actual saved counts are authoritative).
Use each saved inner fit/validation assignment, preserving matched comparisons.
Preprocessing is refitted on the full outer training set only after selection.
Test values are never used in fitting or selection. Do not describe the full
sample score, including training cases, as generalization evidence.

## Evaluation and deliverables

Report individual r, predictive R2, RMSE and mean error in percentage points.
For frozen original bins, average predictions and truths over the SAME held-out
members in one-field and two-field groups; minimum n=10/30/100, partition-balanced
weights. Primary descriptive group comparison uses n>=30, separate orders.
For the fixed full-development seed-08 cases, additionally scan the entire
original arbitrary-order group catalog, deduplicating identical test memberships;
report n>=30 and >=100. Compress by binned profiles using SUMS of individual
predictions, since continuous predictions can differ within an old binned profile.
Overlapping groups and repeated seeds are not independent replication units.

Save splits, raw-field mapping, training preprocessing, selected equation arrays,
candidate scores, held-out row predictions and group diagnostics. Independently
verify dense equation solves, no split leakage, train-only preprocessing, selector
choices, equation reload predictions and group means/r/R2 from row-level outputs.
Use a small synthetic additive/interaction example to check kernel construction
and exact product expansion. Benchmark before the full run. A negative result is
a valid outcome; do not promise a true equation or identify causal mechanisms.

After the fixed experiment, publish a concise bilingual interpretation and
inspectable figures/equations, preserving earlier results and both workbench editions.
