# Updating captured data

1. Obtain a local package you are permitted to use. Keep a copy of its version
   manifest and hash. Do not send account exports or raw emulator data.
2. Import it with `npm run import -- --from ".../public"`.
3. Run `npm run validate:data`. It checks CSV row shapes, primary/composite
   keys, required tables, tower monster joins, map boss joins, island-gate
   source/destination joins and skin-to-character references.
4. Compare the import manifest in `.local/import-manifest.json` with your
   previous capture. Review changes to costs, caps and skills separately from art.
5. Run `npm run test:integration` and `npm run build`.
6. Test the affected screen: open, act, exit, reopen, save/reload.

The import step does not update the public Git repository's captured data.
Tables, skins and media remain local until redistribution permission is reviewed.
A contributor can submit code fixes, synthetic fixtures and a concise report of
which capture/table/IDs changed without uploading the capture itself.

## Adding a new import format

Change `tools/project.py`, retain explicit path allowlists, reject traversal and
symlinks, cap archive size, and add synthetic importer tests. Never extract an
entire APK or arbitrary ZIP into the source tree. Only data is extracted from
the simulation archive; browser_api and engine modules always come from source.

## Build output

The build merges ignored local assets with current `web/public` files, then
rebuilds simulation.zip from `engine/*.py` and imported tables. It also refreshes
the assistant's indexed code chunks. Captured native engine/model files are not
modified by this build. No account or save directory is packaged.

Do not manually edit the generated ZIP, generated knowledge chunks or `dist/`.
Fix their authored inputs and rebuild instead.
