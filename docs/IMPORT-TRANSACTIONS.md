# Local asset import transactions

Stop the development server and run one importer at a time. An import is a full
replacement of the importer-owned `engine/data`, `engine/public`, and
`.local/assets` trees. Files absent from the new pack are removed from those
trees. Authored engine modules and `engine/runtime` saves are outside this scope.

The importer extracts and copies into a temporary directory on the checkout
filesystem, validates the candidate tables, then promotes the trees and manifest
with renames. Handled extraction, copy, validation and promotion failures leave
the old pack in place. The manifest is promoted last. This is rollback protection
for a local offline tool, not a single atomic rename across all four destinations.

If storage also fails during rollback, the error names the retained `.import-*`
directory containing `previous-*` recovery copies. Preserve that directory and
restore the old trees before running the game. Do not commit it or its contents.
Process termination/power loss during promotion and concurrent importers are not
covered by the exception rollback guarantee. Keep the original input pack.
