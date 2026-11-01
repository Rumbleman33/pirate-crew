# Architecture and update map

The shipped game is an authored simulator around a separately captured native
browser client. The simulator is not recovered production server code.

```text
Native client + workbench (web/public)
  -> browser-api.js -> SharedWorker (engine-worker.js)
  -> Pyodide + rebuilt simulation.zip
  -> browser_api.py -> offline_core.py
  -> domain modules -> per-captain IndexedDB save

Registration / social / optional AI
  -> cloud/worker.mjs -> own D1 database + server-only secrets
```

## Engine domains

| Module | Responsibility |
| --- | --- |
| offline_core | persistence, command orchestration, stock, catalog |
| offline_stats | attribute aggregation and CP |
| offline_progression | characters, crew slots, treasures, talents |
| offline_encounters | waves, damage reports, rewards and settlement |
| offline_companions | pets, mounts, books, reins, assignments |
| offline_systems | ships, Haki, fruits, tower and other systems |
| offline_testing | explicit free presets and isolated practice lineups |
| offline_world / offline_stages | map/NPC/fog and stage behavior |
| offline_voyage | One Piece objectives and manual promotion |
| offline_accounts | disposable portable-test account implementation |

Keep protocol IDs and stable save keys unchanged unless a migration is added.
Do not rename all modules just to reorganize imports. Move a bounded behavior
only when its callers and tests can be updated together.

## Native bridge

`testing-ui.js` reuses captured UI classes and module IDs, including the original
tower lineup screen. `runtime-bridge.js` normalizes replies and broadcasts.
`combat-tools.js` observes combat while preserving RNG consumption.
The captured client must match those module IDs; changing its build requires
a compatibility review, not just replacing a bundle.

## Saves

Browser saves are device-local. Preserve the `/pirates/runtime` IDBFS mount and
stable worker name. Bump the worker build handshake together in engine-worker
and browser-api when the runtime changes; old tabs must close once. Additive
stock migrations are versioned and cannot reset chosen upgrades.

Passwords and signing keys are not source constants. Browser-local verifiers
are device-encrypted, registered verifiers are encrypted at rest, and the
production signing key must remain stable across deployments. Changing that
key without a migration prevents decryption of existing registered verifiers.
