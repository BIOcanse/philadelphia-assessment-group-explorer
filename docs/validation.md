# Release validation

Data version: `groups-b5a7e308e8c6`. Release: `v1.0.0`.

- Every browser binary record was compared with the original local arrays: native ID, count, float64 mean, closure and generator. All original high/low ranking sequences and the complete `n >= 100` subsets match.
- All compressed-data SHA-256 values, decompressed lengths, member identifiers, amounts and category codes were checked. Totals are 5,550,736 main groups and 2,048,170 positive-garage groups, excluding the unrestricted baseline.
- The browser edition passed 60 numerical and independence checks, including both cohorts at `n >= 1`, `100` and `500`, full histograms, rank order, conditions, member details, aliases and ID boundaries. Browser API requests were blocked during this test; actual page requests remained on the static file host.
- Both the original local interface and the browser interface passed the same 19 interaction checks: lookup, filters, pagination, plot clicks, export, empty results, and mobile layout. Desktop and 390-pixel mobile screenshots were inspected.
- CSV downloads from the two editions match cell for cell under the same applied filter. Quoting style may differ without changing cells.
- The Windows portable package passed 29 comparisons with the established research API using its included Python 3.13.15 runtime. These include both cohorts, three minimum counts, three sort directions, full histograms, representative/root/profile details, all fields and members, combined filters, CSV cells, and the exact original Excel bytes. Start, status and stop were also exercised.

Machine-readable evidence is in [validation-summary.json](validation-summary.json), [portable-validation.json](portable-validation.json), [browser-package-validation.json](browser-package-validation.json), and [release-manifest.json](release-manifest.json). Release archive hashes are also provided in [SHA256SUMS.txt](SHA256SUMS.txt).

Local response measurements and local file-server browser timings do not establish public-network performance. Research scope, overlapping groups and historical-data limitations are described in [methodology.md](methodology.md).
