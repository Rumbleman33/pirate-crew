# Pirate Crew

Contributor source for the offline game simulator, native testing controls,
guide library and browser workbench. Baseline: offline release v15.

## Start

Install Node 22+ and Python 3.12+. From this folder run:

```sh
npm run dev
```

The launcher installs the pinned development dependencies when needed,
builds the local site, creates a new local signing key, applies local database
migrations and starts at **http://127.0.0.1:8787**. Keep the terminal open.
Windows users can double-click `start.bat`. macOS/Linux users need `python`
to resolve to Python 3 (or set `PIRATE_PYTHON=python3`).

Without a local asset pack, the contributor start page and source checks work.
To play the full recovered game, import assets you are permitted to use:

```sh
npm run import -- --from "path/to/local/site/public"
npm run validate:data
npm run dev
```

The importer accepts the existing v15 public directory containing
`simulation.zip`, `game/`, `pyodide/` and the catalog/media directories.
It excludes saves, account files, secret configuration and captured Python
code. The browser simulation is rebuilt from **this repository's engine code**.
Create a new captain in the local login form. Production logins and API keys
are intentionally absent. This origin has separate browser saves.

## What to edit

| Change | Source |
| --- | --- |
| Guide navigation and reading UI | `web/public/app.mjs`, `library.mjs` |
| Styling | `web/public/style.css`, `futuristic.css`, `play/*.css` |
| Boss selector, lineup, max presets | `web/public/play/testing-ui.js` |
| Native client connection and refresh | `web/public/play/runtime-bridge.js` |
| Combat observation | `web/public/play/combat-tools.js` |
| CP math | `engine/offline_stats.py` |
| Progression, encounters and systems | corresponding `engine/offline_*.py` |
| Authentication, social and assistant APIs | `cloud/` |
| Import, validation, packaging | `tools/project.py` |

The modules keep their current import names to avoid a risky engine rewrite.
See [architecture](docs/ARCHITECTURE.md), [data updates](docs/DATA-UPDATES.md)
and [known limitations](docs/LIMITATIONS.md).

## Check a change

```sh
npm test
npm run check
npm run release:check
```

`npm test` runs source-only unit and JavaScript regressions. With imported
tables, it also runs the captured-data integration suite. Tests generate fresh
temporary accounts; they never copy a developer's passwords or saves.
`npm run test:integration` explicitly requires the imported tables.

## Contribute and preview

Create a branch, make one focused change and open a pull request. CI runs
checks and builds a downloadable preview artifact for every PR, including forks.
Production publication is a separate owner decision; merging cannot silently
deploy the current live game. Optional hosted previews and isolated database
configuration are described in [deployment](docs/DEPLOYMENT.md).

## License and privacy

Authored code is MIT licensed. Captured game/media/table assets and third-party
guides are excluded; see [ASSETS.md](ASSETS.md). Never commit credentials,
exports, private logs or production deployment IDs. Usernames are identifiers,
not secrets; passwords are verified using salted keys, not embedded in code.
See [security](SECURITY.md) before reporting a vulnerability.
