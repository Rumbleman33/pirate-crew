# Checks, previews and releases

Every pull request runs source checks, unit tests and a source-preview build.
CI uploads the `dist/` preview artifact. Download it from the Actions run; it
contains the contributor page and authored browser code, without captured assets.
Fork PRs run without deployment secrets.

## Optional hosted source previews

Hosted source previews use the dedicated `wrangler.preview.jsonc` worker, which
has **no authentication, D1 or production secrets**. It serves only static preview
assets; API routes are disabled. It cannot use the live game's database.

1. Use your own Cloudflare account and a scoped Worker deployment API token.
2. Create a GitHub environment named `preview`. Put `CLOUDFLARE_API_TOKEN` and
   `CLOUDFLARE_ACCOUNT_ID` in that environment's secrets.
3. Initially publish the dedicated preview Worker using
   `npx wrangler deploy --config wrangler.preview.jsonc`.
4. Set repository variable `ENABLE_HOSTED_PREVIEWS=true`.

For same-repository PRs, the optional workflow uploads a new version with alias
`pr-<number>` and writes the result to the job summary. It never promotes that
version to the production game. Forks still receive the downloadable artifact.
Preview versions share only the dedicated stateless preview worker; the game
database is not a binding. See Cloudflare's official Version URL documentation:
https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/

Hosting is not considered configured until a deployment has actually succeeded.
The existing public ChatGPT Site remains managed separately and unchanged.

## Full self-hosted copy

Import permitted assets, run all tests, and provision your own D1 database from
`cloud/migrations`. Copy wrangler.jsonc into ignored `config/deploy.local.json`,
set its actual database ID and a unique worker name, and use the server's secret
store for a newly generated CAPTAIN_AUTH_CONFIG and optional GROQ_API_KEY.
Do not copy the live Site's credentials or connect a preview to its database.

Production authentication signing keys must be kept stable and backed up
privately; encrypted registered verifier records depend on them.
The release source check must pass, and asset redistribution must be approved,
before a public full-game deployment. Owner publication remains a separate step.
