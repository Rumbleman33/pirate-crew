# Security

Do not post passwords, tokens, save exports, account database rows or private
logs in issues. Use GitHub's private vulnerability reporting when enabled;
otherwise contact the maintainer privately before sending sensitive details.

Production secret values, account files and historical Git commits are not
part of this new repository. Local development generates a new signing key
under `.local/`. It never imports the production account list.

`npm run release:check` scans tracked/public candidate source for known secret
formats and forbidden runtime files. This is a useful guard, not proof that
every possible secret format can be detected. Review the staged diff too.

Keep provider keys only in server-side environment secrets. Browser code is
public and is never a safe place to hide passwords or shared API keys. Local
browser saves can be inspected by their owner; authentication is not DRM.
Do not use important personal passwords for a sandbox account.

Fork PRs receive no deployment secrets. Preview credentials and databases must
be distinct from production. Never use `pull_request_target` to run fork code.
If a key is exposed, revoke/rotate it; removing a line is not enough.
