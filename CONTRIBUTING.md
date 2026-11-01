# Contributing

1. Fork or create a branch. Run `npm run dev` and `npm test`.
2. Choose one bug or feature. Use the module map in the README.
3. Add a behavior regression for gameplay/math/persistence changes.
4. Test enter, action, exit, reopen and save/reload for native UI changes.
5. Run `npm run release:check`, then open a PR using the template.

Give reviewers a concrete before/after example, test result and screenshot
for visible changes. Report exact boss IDs and variants; names alone are
ambiguous. Separate confirmed captured behavior from offline assumptions.

Do not include captures, artwork, account exports, credentials or private logs.
Use synthetic examples in public issues. Imported asset directories are
intentionally ignored; changing a table locally does not publish its contents.

Branch owners review changes before merge. CI is required; branch protection
must be enabled by the repository owner after the repository is created.
The live Site is not automatically connected to this repository's main branch.
