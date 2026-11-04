# Guide library implementation and verification

The guide reader is authored in `web/public/guide-content.mjs` and rendered by
`guide-experience.mjs`. It includes 15 guides and 111 chapters. The source-only
build exposes `/guides.html`; the existing contributor landing page links to it.

## Local captured dependencies

Captured reference rows and game artwork remain outside source control under
ASSETS.md. Build a local catalog with:

```
python tools/guide_catalog.py --tables /path/to/permitted/Tables --out .local/assets/data/guide-catalog.json --build CAPTURE_VERSION
npm run build
```

Optional `--packed /path/to/current/refs --manifest /path/to/version.json` makes
current raw fields authoritative and resolves original in-game icon paths.
Original artwork must be available through the existing asset pack/routing.
A missing icon is displayed as unavailable, never replaced by invented artwork.

## Ranking publication gate

The reader withholds tiers until `data/guide-rankings.json` supplies matching-build
engine test coverage for every catalog candidate. Descriptions and raw table
values do not count as comparative tests. Pet role rankings use isolated native skill trials for all 75 pets, with the
fixture and measured metrics embedded in the authored results module. Other
systems do not yet have complete comparative coverage.

Current private build-34521 native mechanical verification:

- 375 pet stage/skill activation cases passed.
- 375 cases passed immediate healing, attribute payloads, cleanse, HoT timing
  and totals, and cooldown-boundary assertions.
- 193,600 ordered buff pairs passed across all 440 pet-origin buffs.
- 15 passive branch cases passed condition and probability-boundary assertions.

These results establish mechanics only. The user selected isolated skill evaluation instead of mixed-roster battles.
The captured mutation-during-buff-iteration bug is documented separately and does
not change the isolated fixture. It has not been patched in the game engine.

## Language selector

Primary navigation has authored translations in ten additional languages.
Full page translation uses the browser Translator API when available. Safari,
mobile, unsupported languages and unavailable models require a configured provider
for full translation. The selector explicitly reports availability and restores
English on failure. Numbers and editable fields are protected. Game canvas text
is outside DOM translation. This is not yet universal site translation.

## Remaining release requirements

Complete comparative coverage, inspect sample counts and uncertainty, and attach
visual evidence after browser QA. The managed static preview serves successfully,
but cloud-browser inspection has repeatedly timed out. No visual pass is claimed.
Use the contribution PR workflow; merging and live publication remain owner actions.
