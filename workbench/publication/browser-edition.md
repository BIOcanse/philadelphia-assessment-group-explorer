# Browser edition — static hosting

Use the [live workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/) or download the [browser ZIP](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.1.0/group-explorer-browser-v1.1.0.zip).

The archive contains `site/`, a standalone GitHub Pages workflow, and instructions. Deploy the contents of `site/` with any static HTTP host. A modern browser with Web Workers and `DecompressionStream` is required. No Python query service, database server, API key or sign-in is needed.

For a local preview, serve the extracted package with a file server and open its `/site/` path. For example, with an existing Python installation:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/site/`. This command only serves files; statistical queries run in the browser. Opening `index.html` directly through `file://` does not provide the HTTP origin required by the Worker and data requests.

## Hosting on GitHub Pages

This repository uses the published release as its deployment input. A release publication starts the Pages workflow, which downloads the browser asset, verifies its SHA-256 checksum, and deploys `site/`. A maintainer can also run the workflow manually with the release tag.

To host the standalone ZIP in another repository, commit its `site/`, `.github/` and README files, then select **Settings → Pages → Source → GitHub Actions**. Push `main` or run **Publish Group Explorer** manually. Relative URLs support repository subpaths and group-ID deep links. Some data files exceed GitHub's browser-upload limit, so use Git for that standalone route.

The default catalog contains every group with at least 100 transactions. Queries with smaller minimum counts download the selected cohort's complete catalog. A direct group-ID lookup can fetch the relevant shard without loading everything. Download progress is shown in the page; the app does not report partial statistics as complete results.

CSV export is limited to the requested first 50,000 matching groups. For every row, download the full Parquet catalog from the workbench. Statistics and canonical IDs match the local edition. The downloadable Excel companion belongs to the local edition.

[GitHub Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
