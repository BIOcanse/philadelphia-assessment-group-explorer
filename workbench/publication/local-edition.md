# Local edition — Windows x64

Download the [portable local ZIP](https://github.com/BIOcanse/philadelphia-assessment-group-explorer/releases/download/v1.1.0/group-explorer-local-windows-x64-v1.1.0.zip), extract the entire archive to a writable folder, and double-click **Start.cmd**. Your browser opens at [http://127.0.0.1:8767/](http://127.0.0.1:8767/). Use **Stop.cmd** to stop this copy.

The package contains Python 3.13.15, NumPy 2.3.5, pandas 3.0.1 and their required dependencies. No Python installation, package download or administrator access is required. The server and data remain on your computer, and all queries work offline. The bundled executable is for Windows x64; use the browser edition on other systems.

The default port is 8767. If another copy is already running, stop that copy or choose another port:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Port 8769 -OpenBrowser
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Port 8769 -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1 -Port 8769 -Action stop
```

The launcher verifies the owning process and refuses to stop a different copy. Logs are written under `outputs/group_workbench/`. Startup verifies the fixed source data checksums. The runtime is package-local and does not modify the machine's Python installation.

The Excel companion is `outputs/group_workbench/Group_ID_Dictionary.xlsx`. It contains all 4,759 complete profiles and 80 focus groups; the full 7,598,906-group catalogs are the two Parquet downloads. Excel URLs use the default local port; if you choose another port, open the app there and paste the group ID.

For source development, use the packaged `runtime/python.exe` to run `workbench/server.py --port 8767`, or use your own environment with `requirements-local.txt`. Runtime downloads and checksums are recorded in `runtime-provenance.json`; third-party licenses accompany their components.

[Online workbench](https://biocanse.github.io/philadelphia-assessment-group-explorer/) · [Repository](https://github.com/BIOcanse/philadelphia-assessment-group-explorer)
