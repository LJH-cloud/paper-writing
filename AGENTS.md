# Installing and maintaining paper-writing

These instructions concern this repository's installation and maintenance. Manuscript work follows `SKILL.md` and the user's current scope.

## Installation requests

- Read `INSTALL.md` and `dependencies.lock.json` before installing.
- A request to install this repository includes the listed companion skills. Run `python3 scripts/install.py` with the intended skills destination, then run the same script with `--check`.
- If a generic skill installer already copied the main skill, continue with its installed `scripts/install.py --dependencies-only`, using the same destination, then run `--check`. Copying the main directory alone is incomplete.
- Preserve existing skills by default. Use `--replace` only when replacement is requested; do not overwrite the host's `.system/imagegen`.
- Report missing or invalid dependencies. File installation does not establish that image generation, MCP servers, accounts, or optional runtime packages are configured.
- Do not execute upstream installation scripts or alter unrelated agent settings.

## Maintenance

- Preserve `references/writing-principles.md` byte-for-byte unless the user explicitly requests a change to the 18 principles.
- Keep dependency names, fixed upstream commits, installation documentation and script behavior consistent.
- Run skill validation and `python3 -m unittest discover -s tests -v` after installer changes. Use temporary destinations for integration tests, never a real user's skills directory.
- Exclude local paths, credentials, caches and manuscript data from commits. Publish only the requested repository changes.
