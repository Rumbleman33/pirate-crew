# Code and asset boundary

The public repository contains authored source. It excludes the captured
game client, APKs, media, reference tables and third-party guide documents.
Their presence in a local capture is not treated as permission to redistribute.

`npm run import -- --from "path/to/your/local/site/public"` imports a local
asset package you are permitted to use. It never downloads from a game server.
Imported media lives in `.local/assets`; captured tables live in `engine/data`.
Both directories are ignored by Git. The importer uses an explicit allowlist,
rejects symlinks and credential/save file names, and records SHA-256 hashes.

The original native game runtime remains a separately supplied dependency.
The authored patches in `web/public/play` reference its module IDs; they do
not pretend to implement that runtime from scratch. Third-party guide PDFs
and embedded sources are also separate dependencies.

Node, Python, Wrangler, Pyodide and other separately supplied libraries retain
their respective licenses. Install Wrangler using the pinned package lock.
If distributing an authorized Pyodide/media pack, retain its upstream notices.

Do not attach a full capture to a public issue, release or pull request.
An asset import manifest identifies local files and integrity, not ownership
or permission. Release approval for captured content is a separate decision.
