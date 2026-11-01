# Known limitations

- The authoritative live server formula is unavailable. Some stacking rules,
  particularly ship-room inheritance, are explicit offline models.
- Not every recovered protocol/UI feature has a local implementation. Opening
  a native screen does not prove its server behavior is implemented.
- Native module IDs depend on the captured client build. The current patches
  target the existing offline-v15 client; a different APK needs compatibility work.
- Boss practice uses captured stats and authored variants. It does not invent
  arbitrary enemy levels. Ordinary map and island-unlock bosses can share names
  but have different stats and IDs.
- Unit CI is source-only. The captured-data integration suite and full gameplay
  require a permitted local asset import. CI reports this distinction explicitly.
- Browser saves are not cloud backups. Export before clearing browser storage.
- Local authentication is separate from the hosted Site. The original ten
  production test credentials are deliberately not included.
- Source-preview artifacts do not include the full game, captured media or
  third-party guides. Hosted preview configuration is opt-in and separate from
  the existing Site deployment.
